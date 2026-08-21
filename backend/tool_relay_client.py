from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import suppress

import websockets

from backend.credential_store import load_relay_secret
from backend.local_tool_dispatcher import local_tool_dispatcher


logger = logging.getLogger("sherpa.tool_relay")


class ToolRelayClient:
    def __init__(self) -> None:
        self.url = os.getenv("SHERPA_TOOL_RELAY_URL", "").rstrip("/")
        self.secret = load_relay_secret() or ""
        self.installation_id = os.getenv("SHERPA_INSTALLATION_ID", "default")
        self._task: asyncio.Task[None] | None = None
        self._connected = asyncio.Event()

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.secret)

    def start(self) -> None:
        if self.enabled and not self._task:
            self._task = asyncio.create_task(self._run(), name="tool-relay")

    async def close(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def wait_until_connected(self, timeout: float = 15) -> None:
        await asyncio.wait_for(self._connected.wait(), timeout=timeout)

    async def _run(self) -> None:
        delay = 1
        while True:
            try:
                await self._connect()
                delay = 1
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.warning("relay.disconnected error=%s reconnect_seconds=%d", error, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)

    async def _connect(self) -> None:
        websocket_url = self.url.replace("https://", "wss://", 1).replace(
            "http://", "ws://", 1
        )
        uri = f"{websocket_url}/desktop/connect/{self.installation_id}"
        async with websockets.connect(
            uri,
            additional_headers={"Authorization": f"Bearer {self.secret}"},
            max_size=8 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=20,
        ) as socket:
            self._connected.set()
            logger.info("relay.connected installation=%s", self.installation_id)
            try:
                async for raw in socket:
                    message = json.loads(raw)
                    if message.get("type") != "tool_call":
                        continue
                    asyncio.create_task(
                        self._handle(socket, message),
                        name=f"relay:{message.get('call_id', 'unknown')}",
                    )
            finally:
                self._connected.clear()

    async def _handle(self, socket: object, message: dict[str, object]) -> None:
        call_id = str(message.get("call_id") or "")
        result = await local_tool_dispatcher.run(
            name=str(message.get("name") or ""),
            args=dict(message.get("args") or {}),
            state=dict(message.get("state") or {}),
            function_call_id=str(message.get("function_call_id") or call_id),
            session_id=str(message.get("session_id") or "remote"),
        )
        await socket.send(json.dumps({  # type: ignore[attr-defined]
            "type": "tool_result",
            "call_id": call_id,
            "result": result,
        }, default=str))


tool_relay_client = ToolRelayClient()
