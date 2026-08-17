import unittest
from unittest.mock import MagicMock, patch

from backend.tools.memory import save_memory


class ExplicitMemoryToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_saves_verified_memory_against_its_task(self) -> None:
        tool_context = MagicMock()
        tool_context.session.id = "voice-chat:task-123"

        with (
            patch("backend.tools.memory.memory_store.snapshot", return_value={"settings": {"enabled": True}}),
            patch("backend.tools.memory.memory_store.remember") as remember,
        ):
            result = await save_memory(
                "workflow",
                "Use Google Sheets for requested spreadsheets",
                tool_context,
            )

        self.assertEqual(result["status"], "saved")
        remember.assert_called_once_with(
            category="workflow",
            content="Use Google Sheets for requested spreadsheets",
            source_type="task",
            source_id="task-123",
            editable=True,
        )

    async def test_explicit_save_fails_when_memory_is_disabled(self) -> None:
        tool_context = MagicMock()
        tool_context.session.id = "voice-chat:task-123"

        with patch(
            "backend.tools.memory.memory_store.snapshot",
            return_value={"settings": {"enabled": False}},
        ):
            result = await save_memory("preference", "Call him Ben", tool_context)

        self.assertEqual(result["status"], "failed")
        self.assertIn("disabled", result["error"])


if __name__ == "__main__":
    unittest.main()
