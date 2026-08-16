import unittest

from backend.tools.browser_use.playwright import BROWSER_TOOL_NAMES
from backend.tools.computer_use.callbacks import normalize_tool_args, sanitize_tool_response


class BrowserCodeTests(unittest.TestCase):
    def test_page_scoped_code_tool_is_exposed(self) -> None:
        self.assertIn("browser_evaluate", BROWSER_TOOL_NAMES)
        self.assertNotIn("browser_run_code_unsafe", BROWSER_TOOL_NAMES)

    def test_allows_bounded_dom_transformation(self) -> None:
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

    def test_rejects_file_and_oversized_code(self) -> None:
        self.assertIn(
            "files is disabled",
            normalize_tool_args("browser_evaluate", {"filename": "script.js"}) or "",
        )
        self.assertIn(
            "character limit",
            normalize_tool_args("browser_evaluate", {"function": "x" * 6001}) or "",
        )

    def test_snapshot_defaults_to_bounded_depth(self) -> None:
        args = {}

        self.assertIsNone(normalize_tool_args("browser_snapshot", args))
        self.assertEqual(args["depth"], 12)

    def test_tool_text_budget_applies_across_blocks(self) -> None:
        response = sanitize_tool_response({
            "content": [
                {"type": "text", "text": "a" * 15_000},
                {"type": "text", "text": "b" * 15_000},
            ]
        })

        self.assertEqual(sum(len(block["text"]) for block in response["content"]), 20_000)


if __name__ == "__main__":
    unittest.main()
