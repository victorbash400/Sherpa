import base64
import unittest
from unittest.mock import patch

from backend.tools.google_tools.mcp import create_google_cloud_toolsets
from backend.tools.google_tools.workspace import (
    WorkspaceApiError,
    create_workspace_toolsets,
    document_text,
    gmail_body,
    google_resource_id,
    workspace_sheets_create_spreadsheet,
)


class WorkspaceToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_workspace_tools_are_direct_and_product_scoped(self) -> None:
        with patch("backend.tools.google_tools.workspace.permission_store.enabled", return_value=True):
            with patch(
                "backend.tools.google_tools.workspace.google_auth.snapshot",
                return_value={"connected": True},
            ):
                toolsets = create_workspace_toolsets()
                tools = [tool for toolset in toolsets for tool in await toolset.get_tools()]

        names = [tool.name for tool in tools]
        self.assertEqual(len(names), 28)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("workspace_gmail_search_threads", names)
        self.assertIn("workspace_docs_create_doc", names)
        self.assertIn("workspace_docs_batch_update", names)
        self.assertIn("workspace_slides_batch_update", names)
        self.assertEqual(len(create_google_cloud_toolsets()), 2)

    def test_google_resource_id_accepts_ids_and_urls(self) -> None:
        resource_id = "1abcdefghijklmnopqrstuvwxyzABCDE"
        self.assertEqual(google_resource_id(resource_id), resource_id)
        self.assertEqual(
            google_resource_id(f"https://docs.google.com/document/d/{resource_id}/edit"),
            resource_id,
        )
        with self.assertRaises(WorkspaceApiError):
            google_resource_id("not-an-id")

    def test_gmail_body_decodes_nested_plain_text(self) -> None:
        encoded = base64.urlsafe_b64encode(b"Prize details").decode().rstrip("=")
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [{"mimeType": "text/plain", "body": {"data": encoded}}],
        }
        self.assertEqual(gmail_body(payload), "Prize details")

    def test_document_text_flattens_paragraph_runs(self) -> None:
        document = {
            "body": {
                "content": [{
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Hello "}},
                            {"textRun": {"content": "world"}},
                        ]
                    }
                }]
            }
        }
        self.assertEqual(document_text(document), "Hello world")

    async def test_created_spreadsheet_returns_real_sheet_ids(self) -> None:
        response = {
            "spreadsheetId": "1abcdefghijklmnopqrstuvwxyzABCDE",
            "spreadsheetUrl": "https://docs.google.com/spreadsheets/example",
            "sheets": [{"properties": {"sheetId": 417, "title": "Ranked Videos", "index": 0}}],
        }
        with patch("backend.tools.google_tools.workspace.workspace_request", return_value=response):
            result = await workspace_sheets_create_spreadsheet("Videos", ["Ranked Videos"])

        self.assertEqual(result["sheets"], [{
            "sheet_id": 417,
            "title": "Ranked Videos",
            "index": 0,
        }])


if __name__ == "__main__":
    unittest.main()
