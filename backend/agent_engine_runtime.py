from __future__ import annotations

import asyncio
import json
import os
from functools import lru_cache
from typing import Any, AsyncIterator

import vertexai
import httpx
from google.adk.events import Event
from google.genai import types
from vertexai import agent_engines


PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "sherpa-20260813")
LOCATION = os.getenv("SHERPA_AGENT_ENGINE_LOCATION", "europe-west1")
RESOURCE = os.getenv("SHERPA_AGENT_ENGINE_RESOURCE", "").strip()
API_URL = os.getenv("SHERPA_AGENT_API_URL", "").rstrip("/")


def enabled() -> bool:
    return bool(RESOURCE)


@lru_cache(maxsize=1)
def remote_app() -> Any:
    if not RESOURCE:
        raise RuntimeError("Sherpa Agent Engine is not configured")
    vertexai.init(project=PROJECT, location=LOCATION, api_transport="rest")
    return agent_engines.get(RESOURCE)


async def get_session(user_id: str, session_id: str) -> dict[str, Any] | None:
    if API_URL:
        return None
    try:
        return await asyncio.to_thread(
            remote_app().get_session,
            user_id=user_id,
            session_id=session_id,
        )
    except Exception as error:
        if "not found" in str(error).casefold() or "404" in str(error):
            return None
        raise


async def ensure_session(
    user_id: str,
    session_id: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    if API_URL:
        from backend.tool_relay_client import tool_relay_client

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{API_URL}/desktop/agent/session",
                headers={"Authorization": f"Bearer {tool_relay_client.secret}"},
                json={
                    "installation_id": tool_relay_client.installation_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "state": state,
                },
            )
        response.raise_for_status()
        return response.json()
    current = await get_session(user_id, session_id)
    if current:
        return current
    return await asyncio.to_thread(
        remote_app().create_session,
        user_id=user_id,
        session_id=session_id,
        state=state,
    )


def parse_stream_json(buffer: str, data: bytes) -> tuple[str, list[object]]:
    buffer += data.decode("utf-8")
    decoder = json.JSONDecoder()
    payloads: list[object] = []
    while buffer.lstrip():
        buffer = buffer.lstrip()
        try:
            payload, offset = decoder.raw_decode(buffer)
        except json.JSONDecodeError:
            break
        buffer = buffer[offset:]
        payloads.extend(payload if isinstance(payload, list) else [payload])
    return buffer, payloads


async def stream_events(
    *,
    user_id: str,
    session_id: str,
    content: types.Content,
) -> AsyncIterator[Event]:
    if API_URL:
        from backend.tool_relay_client import tool_relay_client

        buffer = ""
        received = False
        async with httpx.AsyncClient(timeout=httpx.Timeout(3600, connect=30)) as client:
            async with client.stream(
                "POST",
                f"{API_URL}/desktop/agent/stream",
                headers={"Authorization": f"Bearer {tool_relay_client.secret}"},
                json={
                    "installation_id": tool_relay_client.installation_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "state": {},
                    "message": content.model_dump(mode="json", exclude_none=True),
                },
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    buffer, payloads = parse_stream_json(buffer, chunk)
                    for payload in payloads:
                        received = True
                        yield Event.model_validate(payload)
        if buffer.strip():
            raise RuntimeError("Agent Engine ended with an incomplete event")
        if not received:
            raise RuntimeError("Agent Engine returned no events")
        return
    app = remote_app()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[object] = asyncio.Queue()
    complete = object()

    def consume() -> None:
        response = None
        try:
            buffer = ""
            response = app.execution_api_client.transport._session.post(
                f"https://{LOCATION}-aiplatform.googleapis.com/v1/{app.resource_name}:streamQuery",
                json={
                    "classMethod": "async_stream_query",
                    "input": {
                        "user_id": user_id,
                        "session_id": session_id,
                        "message": content.model_dump(mode="json", exclude_none=True),
                        "run_config": {"streaming_mode": "sse"},
                    },
                },
                stream=True,
                timeout=(30, 3600),
            )
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=None):
                buffer, payloads = parse_stream_json(buffer, chunk)
                for payload in payloads:
                    if payload is not None:
                        loop.call_soon_threadsafe(queue.put_nowait, payload)
            if buffer.strip():
                raise RuntimeError("Agent Engine ended with an incomplete event")
        except BaseException as error:
            loop.call_soon_threadsafe(queue.put_nowait, error)
        finally:
            if response is not None:
                response.close()
            loop.call_soon_threadsafe(queue.put_nowait, complete)

    consumer = asyncio.create_task(asyncio.to_thread(consume))
    received = False
    while True:
        item = await queue.get()
        if item is complete:
            break
        if isinstance(item, BaseException):
            raise item
        received = True
        yield Event.model_validate(item)
    await consumer
    if not received:
        raise RuntimeError("Agent Engine returned no events")
