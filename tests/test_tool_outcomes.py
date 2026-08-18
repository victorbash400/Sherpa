import tempfile
import unittest
from pathlib import Path

from backend.tools.computer_use.callbacks import (
    normalize_tool_args,
    normalize_tool_outcome,
)


class ToolOutcomeTests(unittest.TestCase):
    def test_download_transport_error_becomes_started_outcome(self) -> None:
        result = normalize_tool_outcome(
            "browser_navigate",
            {"url": "https://example.test/export.xlsx"},
            {
                "isError": True,
                "content": [{"type": "text", "text": "Error: Download is starting"}],
            },
        )

        self.assertEqual(result["status"], "download_started")
        self.assertTrue(result["verification_required"])
        self.assertNotIn("isError", result)

    def test_unknown_tool_error_remains_failure(self) -> None:
        original = {"status": "failed", "error": "Navigation crashed"}

        result = normalize_tool_outcome("browser_navigate", {}, original)

        self.assertEqual(result, original)

    def test_download_signal_from_click_is_also_preserved(self) -> None:
        result = normalize_tool_outcome(
            "browser_click",
            {"element": "Download"},
            {"status": "failed", "error": "Download is starting"},
        )

        self.assertEqual(result["status"], "download_started")

    def test_dialog_rejects_missing_owner(self) -> None:
        error = normalize_tool_args("computer_dialog", {"action": "list"})

        self.assertIn("app, PID, or exact window ID", error or "")

    def test_file_dialog_rejects_missing_local_file(self) -> None:
        error = normalize_tool_args("computer_dialog", {
            "action": "file",
            "app": "TextEdit",
            "path": "/tmp/file-that-does-not-exist.txt",
        })

        self.assertIn("does not exist", error or "")

    def test_file_dialog_accepts_complete_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "attachment.txt"
            file_path.write_text("ready")
            args = {
                "action": "file",
                "app": "TextEdit",
                "path": str(file_path),
            }

            self.assertIsNone(normalize_tool_args("computer_dialog", args))

    def test_dialog_normalizes_compound_pid_and_window_title(self) -> None:
        args = {"action": "list", "app": "PID:76387:Open"}

        self.assertIsNone(normalize_tool_args("computer_dialog", args))
        self.assertEqual(args, {"action": "list", "pid": 76387, "window_title": "Open"})


if __name__ == "__main__":
    unittest.main()
