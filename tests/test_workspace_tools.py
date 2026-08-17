import base64
from email import policy
from email.parser import BytesParser
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from backend.tools.google_tools.mcp import create_google_cloud_toolsets
from backend.tools.google_tools.workspace import (
    WorkspaceApiError,
    create_workspace_toolsets,
    document_text,
    gmail_body,
    google_resource_id,
    workspace_sheets_create_spreadsheet,
    workspace_calendar_create_event,
)
from backend.tools.google_tools.workspace_drive import workspace_drive_upload_file
from backend.tools.google_tools.workspace_forms import workspace_forms_create_form
from backend.tools.google_tools.workspace_gmail import workspace_gmail_send_rich_message
from backend.tools.google_tools.workspace_meet import workspace_meet_list_conferences
from backend.tools.google_tools.workspace_tasks import workspace_tasks_update_task


class WorkspaceToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_workspace_tools_are_direct_and_product_scoped(self) -> None:
        with patch("backend.tools.google_tools.workspace_core.permission_store.enabled", return_value=True):
            with patch(
                "backend.tools.google_tools.workspace_core.google_auth.snapshot",
                return_value={"connected": True},
            ):
                toolsets = create_workspace_toolsets()
                tools = [tool for toolset in toolsets for tool in await toolset.get_tools()]

        names = [tool.name for tool in tools]
        self.assertEqual(len(names), 76)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("workspace_gmail_search_threads", names)
        self.assertIn("workspace_docs_create_doc", names)
        self.assertIn("workspace_docs_batch_update", names)
        self.assertIn("workspace_slides_batch_update", names)
        self.assertIn("workspace_gmail_reply", names)
        self.assertIn("workspace_drive_share_file", names)
        self.assertIn("workspace_tasks_create_task", names)
        self.assertIn("workspace_forms_create_form", names)
        self.assertIn("workspace_meet_list_transcript_entries", names)
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

    async def test_rich_gmail_message_contains_html_and_attachment(self) -> None:
        request = AsyncMock(return_value={"id": "message-1", "threadId": "thread-1"})
        with patch("backend.tools.google_tools.workspace_gmail.workspace_request", request):
            result = await workspace_gmail_send_rich_message(
                ["recipient@example.com"],
                "Test",
                "Plain",
                html_body="<strong>HTML</strong>",
                attachments=[{
                    "filename": "note.txt",
                    "mime_type": "text/plain",
                    "data_base64": base64.b64encode(b"Attachment").decode(),
                }],
            )

        payload = request.await_args.kwargs["json"]
        raw = base64.urlsafe_b64decode(payload["raw"] + "=" * (-len(payload["raw"]) % 4))
        message = BytesParser(policy=policy.default).parsebytes(raw)
        self.assertEqual(message["To"], "recipient@example.com")
        self.assertEqual(message.get_body(preferencelist=("html",)).get_content(), "<strong>HTML</strong>\n")
        self.assertEqual(next(message.iter_attachments()).get_payload(decode=True), b"Attachment")
        self.assertEqual(result["status"], "sent")

    async def test_drive_upload_uses_multipart_media_body(self) -> None:
        response = SimpleNamespace(json=lambda: {"id": "file-1", "name": "note.txt"})
        request = AsyncMock(return_value=response)
        with patch("backend.tools.google_tools.workspace_drive.workspace_response", request):
            result = await workspace_drive_upload_file(
                "note.txt",
                base64.b64encode(b"hello").decode(),
                "text/plain",
            )

        body = request.await_args.kwargs["content"]
        self.assertIn(b'"name": "note.txt"', body)
        self.assertIn(b"hello", body)
        self.assertEqual(result["id"], "file-1")

    async def test_task_completion_maps_to_google_status(self) -> None:
        request = AsyncMock(return_value={"id": "task-1", "status": "completed"})
        with patch("backend.tools.google_tools.workspace_tasks.workspace_request", request):
            await workspace_tasks_update_task("task-1", completed=True)
        self.assertEqual(request.await_args.kwargs["json"]["status"], "completed")

    async def test_calendar_create_can_request_meet_and_attendees(self) -> None:
        request = AsyncMock(return_value={"id": "event-1", "hangoutLink": "https://meet.google.com/abc-defg-hij"})
        with patch("backend.tools.google_tools.workspace.workspace_request", request):
            result = await workspace_calendar_create_event(
                "Planning",
                "2026-08-18T10:00:00+03:00",
                "2026-08-18T10:30:00+03:00",
                attendees=["person@example.com"],
                create_meet_link=True,
            )
        payload = request.await_args.kwargs["json"]
        self.assertEqual(payload["attendees"], [{"email": "person@example.com"}])
        self.assertEqual(payload["conferenceData"]["createRequest"]["conferenceSolutionKey"]["type"], "hangoutsMeet")
        self.assertEqual(result["meet_link"], "https://meet.google.com/abc-defg-hij")

    async def test_form_create_returns_edit_and_preview_metadata(self) -> None:
        request = AsyncMock(return_value={"formId": "1abcdefghijklmnopqrstuvwxyzABCDE", "info": {"title": "Survey"}})
        with patch("backend.tools.google_tools.workspace_forms.workspace_request", request):
            result = await workspace_forms_create_form("Survey")
        self.assertIn(result["form_id"], result["edit_url"])
        self.assertEqual(result["preview"]["mime_type"], "application/vnd.google-apps.form")

    async def test_meet_conference_filter_is_explicit(self) -> None:
        request = AsyncMock(return_value={"conferenceRecords": []})
        with patch("backend.tools.google_tools.workspace_meet.workspace_request", request):
            await workspace_meet_list_conferences("abc-defg-hij", active_only=True)
        self.assertEqual(
            request.await_args.kwargs["params"]["filter"],
            'space.meeting_code = "abc-defg-hij" AND end_time IS NULL',
        )


if __name__ == "__main__":
    unittest.main()
