from __future__ import annotations

import asyncio
import hmac
import os
from dataclasses import dataclass, field
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field


INTERNAL_SECRET = os.getenv("SHERPA_INTERNAL_SECRET", "")
TOOL_TIMEOUT_SECONDS = int(os.getenv("SHERPA_TOOL_TIMEOUT_SECONDS", "900"))


class ToolRequest(BaseModel):
    installation_id: str = Field(min_length=1, max_length=100)
    function_call_id: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)


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


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "connected_desktops": len(relay.connections)}


@app.websocket("/desktop/connect/{installation_id}")
async def desktop_connect(socket: WebSocket, installation_id: str) -> None:
    authorization = socket.headers.get("authorization", "")
    if not authorization.startswith("Bearer ") or not authorized(authorization[7:]):
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
