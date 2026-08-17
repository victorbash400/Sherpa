import unittest

from backend.tools.browser_use.playwright import BROWSER_TOOL_NAMES
from backend.tools.computer_use.callbacks import normalize_tool_args, sanitize_tool_response
from backend.tools.computer_use.peekaboo import PEEKABOO_TOOL_NAMES


class BrowserCodeTests(unittest.TestCase):
    def test_worker_does_not_expose_screenshot_tool(self) -> None:
        self.assertNotIn("see", PEEKABOO_TOOL_NAMES)

    def test_page_scoped_code_tool_is_exposed(self) -> None:
        self.assertIn("browser_evaluate", BROWSER_TOOL_NAMES)
        self.assertNotIn("browser_run_code_unsafe", BROWSER_TOOL_NAMES)

    def test_allows_dom_transformation(self) -> None:
        args = {
            "function": "() => [...document.querySelectorAll('input')].map((el) => el.value = 'Draft').length"
        }

        self.assertIsNone(normalize_tool_args("browser_evaluate", args))

    def test_rejects_network_storage_navigation_and_dynamic_code(self) -> None:
        snippets = (
            "() => fetch('/api/send')",
            "() => localStorage.clear()",
            "() => { window.location = '/done' }",
            "() => eval('document.body.remove()')",
            "() => document.querySelector('form').requestSubmit()",
        )

        for code in snippets:
            with self.subTest(code=code):
                error = normalize_tool_args("browser_evaluate", {"function": code})
                self.assertIn("disabled", error or "")

    def test_rejects_loading_code_from_a_file(self) -> None:
        self.assertIn(
            "files is disabled",
            normalize_tool_args("browser_evaluate", {"filename": "script.js"}) or "",
        )
    def test_long_inline_code_is_not_rejected_by_length(self) -> None:
        code = "() => '" + ("x" * 30_000) + "'"

        self.assertIsNone(normalize_tool_args("browser_evaluate", {"function": code}))

    def test_snapshot_depth_is_not_changed(self) -> None:
        args = {}

        self.assertIsNone(normalize_tool_args("browser_snapshot", args))
        self.assertNotIn("depth", args)

    def test_invalid_app_open_action_points_to_launch(self) -> None:
        error = normalize_tool_args("computer_app", {"action": "open", "app": "Finder"})

        self.assertIn("action=launch", error or "")

    def test_tool_text_is_preserved_across_blocks(self) -> None:
        response = sanitize_tool_response({
            "content": [
                {"type": "text", "text": "a" * 15_000},
                {"type": "text", "text": "b" * 15_000},
            ]
        })

        self.assertEqual(sum(len(block["text"]) for block in response["content"]), 30_000)

    def test_see_omits_pixels_but_preserves_structured_metadata(self) -> None:
        response = sanitize_tool_response({
            "content": [
                {"type": "text", "text": "window"},
                {"type": "image", "data": "pixels", "mimeType": "image/png"},
            ],
            "_meta": {"window_id": 42},
        }, "computer_see")

        self.assertEqual(response["content"], [{"type": "text", "text": "window"}])
        self.assertEqual(response["media_omitted"], 1)
        self.assertEqual(response["metadata"]["window_id"], 42)

    def test_non_visual_tools_still_omit_pixels(self) -> None:
        response = sanitize_tool_response({
            "content": [{"type": "image", "data": "pixels"}],
        }, "computer_inspect_ui")

        self.assertEqual(response["content"], [])
        self.assertEqual(response["media_omitted"], 1)


if __name__ == "__main__":
    unittest.main()
