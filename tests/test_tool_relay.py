from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("SHERPA_INTERNAL_SECRET", "test-secret")

from fastapi import HTTPException

from cloud.relay.main import Relay, authorized_desktop, desktop_token


class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    async def send_json(self, payload: dict[str, object]) -> None:
        self.sent.append(payload)

    async def close(self, **_: object) -> None:
        return None


class ToolRelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_desktop_token_is_bound_to_the_installation(self) -> None:
        token = desktop_token("desktop-a")
        self.assertTrue(authorized_desktop("desktop-a", token))
        self.assertFalse(authorized_desktop("desktop-b", token))

    async def test_call_fails_explicitly_without_a_desktop(self) -> None:
        relay = Relay()
        with self.assertRaises(HTTPException) as raised:
            await relay.call("missing", {"name": "computer_action"})
        self.assertEqual(raised.exception.status_code, 409)

    async def test_call_resolves_matching_websocket_result(self) -> None:
        relay = Relay()
        socket = FakeSocket()
        await relay.connect("desktop", socket)  # type: ignore[arg-type]

        pending = asyncio.create_task(
            relay.call("desktop", {"name": "computer_action", "args": {}})
        )
        await asyncio.sleep(0)
        call_id = str(socket.sent[0]["call_id"])
        relay.resolve(call_id, {"status": "ok"})

        self.assertEqual(await pending, {"status": "ok"})
        self.assertNotIn(call_id, relay.pending)

    async def test_connection_replacement_closes_previous_socket(self) -> None:
        relay = Relay()
        first = FakeSocket()
        second = FakeSocket()
        first.close = AsyncMock()  # type: ignore[method-assign]
        await relay.connect("desktop", first)  # type: ignore[arg-type]
        await relay.connect("desktop", second)  # type: ignore[arg-type]
        first.close.assert_awaited_once()
        self.assertIs(relay.connections["desktop"].socket, second)


if __name__ == "__main__":
    unittest.main()
