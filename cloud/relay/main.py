from __future__ import annotations

import asyncio
import hmac
import hashlib
import os
from dataclasses import dataclass, field
from typing import Annotated, Any
from uuid import uuid4

import google.auth
from google.auth.transport.requests import Request
import httpx
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


INTERNAL_SECRET = os.getenv("SHERPA_INTERNAL_SECRET", "")
TOOL_TIMEOUT_SECONDS = int(os.getenv("SHERPA_TOOL_TIMEOUT_SECONDS", "900"))
AGENT_ENGINE_RESOURCE = os.getenv("SHERPA_AGENT_ENGINE_RESOURCE", "")
AGENT_ENGINE_LOCATION = os.getenv("SHERPA_AGENT_ENGINE_LOCATION", "europe-west1")
credentials, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
credential_lock = asyncio.Lock()


class ToolRequest(BaseModel):
    installation_id: str = Field(min_length=1, max_length=100)
    function_call_id: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)


class DesktopRegistration(BaseModel):
    installation_id: str
    token: str


class AgentSessionRequest(BaseModel):
    installation_id: str
    user_id: str
    session_id: str
    state: dict[str, Any] = Field(default_factory=dict)


class AgentStreamRequest(AgentSessionRequest):
    message: dict[str, Any]


@dataclass
class DesktopConnection:
    socket: WebSocket
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class Relay:
    def __init__(self) -> None:
        self.connections: dict[str, DesktopConnection] = {}
        self.pending: dict[str, asyncio.Future[Any]] = {}

    async def connect(self, installation_id: str, socket: WebSocket) -> None:
        previous = self.connections.get(installation_id)
        if previous:
            await previous.socket.close(code=1012, reason="Replaced by a new Sherpa connection")
        self.connections[installation_id] = DesktopConnection(socket)

    def disconnect(self, installation_id: str, socket: WebSocket) -> None:
        current = self.connections.get(installation_id)
        if current and current.socket is socket:
            self.connections.pop(installation_id, None)

    async def call(self, installation_id: str, payload: dict[str, Any]) -> Any:
        connection = self.connections.get(installation_id)
        if not connection:
            raise HTTPException(status_code=409, detail="Sherpa desktop is not connected")
        call_id = str(uuid4())
        future = asyncio.get_running_loop().create_future()
        self.pending[call_id] = future
        try:
            async with connection.send_lock:
                await connection.socket.send_json({
                    "type": "tool_call",
                    "call_id": call_id,
                    **payload,
                })
            return await asyncio.wait_for(future, timeout=TOOL_TIMEOUT_SECONDS)
        except TimeoutError as error:
            raise HTTPException(status_code=504, detail="Local tool execution timed out") from error
        finally:
            self.pending.pop(call_id, None)

    def resolve(self, call_id: str, result: Any) -> None:
        future = self.pending.get(call_id)
        if future and not future.done():
            future.set_result(result)


relay = Relay()
app = FastAPI(title="Sherpa Tool Relay")


def authorized(value: str) -> bool:
    return bool(INTERNAL_SECRET and hmac.compare_digest(value, INTERNAL_SECRET))


def desktop_token(installation_id: str) -> str:
    return hmac.new(
        INTERNAL_SECRET.encode(),
        installation_id.encode(),
        hashlib.sha256,
    ).hexdigest()


def authorized_desktop(installation_id: str, value: str) -> bool:
    return bool(
        INTERNAL_SECRET
        and value
        and hmac.compare_digest(value, desktop_token(installation_id))
    )


async def vertex_headers() -> dict[str, str]:
    async with credential_lock:
        if not credentials.valid:
            await asyncio.to_thread(credentials.refresh, Request())
        return {"Authorization": f"Bearer {credentials.token}"}


def require_desktop(installation_id: str, authorization: str | None) -> None:
    token = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if not authorized_desktop(installation_id, token):
        raise HTTPException(status_code=401, detail="Desktop authentication failed")


def agent_engine_url(method: str) -> str:
    if not AGENT_ENGINE_RESOURCE:
        raise HTTPException(status_code=503, detail="Agent Engine is not configured")
    return (
        f"https://{AGENT_ENGINE_LOCATION}-aiplatform.googleapis.com/v1/"
        f"{AGENT_ENGINE_RESOURCE}:{method}"
    )


async def agent_query(class_method: str, input_data: dict[str, Any]) -> Any:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            agent_engine_url("query"),
            headers=await vertex_headers(),
            json={"classMethod": class_method, "input": input_data},
        )
    if response.is_error:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json().get("output")


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "connected_desktops": len(relay.connections)}


@app.post("/desktop/register")
async def desktop_register() -> DesktopRegistration:
    installation_id = str(uuid4())
    return DesktopRegistration(
        installation_id=installation_id,
        token=desktop_token(installation_id),
    )


@app.post("/desktop/agent/session")
async def desktop_agent_session(
    body: AgentSessionRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> Any:
    require_desktop(body.installation_id, authorization)
    try:
        return await agent_query("async_get_session", {
            "user_id": body.user_id,
            "session_id": body.session_id,
        })
    except HTTPException as error:
        if error.status_code != 404 and "Session not found" not in str(error.detail):
            raise
    return await agent_query("async_create_session", {
        "user_id": body.user_id,
        "session_id": body.session_id,
        "state": body.state,
    })


@app.post("/desktop/agent/stream")
async def desktop_agent_stream(
    body: AgentStreamRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    require_desktop(body.installation_id, authorization)

    async def events():
        async with httpx.AsyncClient(timeout=httpx.Timeout(3600, connect=30)) as client:
            async with client.stream(
                "POST",
                agent_engine_url("streamQuery"),
                headers=await vertex_headers(),
                json={
                    "classMethod": "async_stream_query",
                    "input": {
                        "user_id": body.user_id,
                        "session_id": body.session_id,
                        "message": body.message,
                        "run_config": {"streaming_mode": "sse"},
                    },
                },
            ) as response:
                if response.is_error:
                    detail = await response.aread()
                    raise HTTPException(status_code=response.status_code, detail=detail.decode())
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(events(), media_type="application/json")


@app.websocket("/desktop/connect/{installation_id}")
async def desktop_connect(socket: WebSocket, installation_id: str) -> None:
    authorization = socket.headers.get("authorization", "")
    if not authorization.startswith("Bearer ") or not authorized_desktop(
        installation_id,
        authorization[7:],
    ):
        await socket.close(code=1008, reason="Unauthorized")
        return
    await socket.accept()
    await relay.connect(installation_id, socket)
    try:
        while True:
            message = await socket.receive_json()
            if message.get("type") == "tool_result":
                relay.resolve(str(message.get("call_id") or ""), message.get("result"))
    except WebSocketDisconnect:
        pass
    finally:
        relay.disconnect(installation_id, socket)


@app.post("/agent/tools/{tool_name}")
async def agent_tool(
    tool_name: str,
    body: ToolRequest,
    agent_secret: Annotated[str | None, Header(alias="X-Sherpa-Agent-Secret")] = None,
) -> Any:
    if not agent_secret or not authorized(agent_secret):
        raise HTTPException(status_code=401, detail="Agent tool authentication failed")
    return await relay.call(body.installation_id, {
        "name": tool_name,
        "function_call_id": body.function_call_id,
        "args": body.args,
        "state": body.state,
        "session_id": str(body.state.get("session_id") or "remote"),
    })
