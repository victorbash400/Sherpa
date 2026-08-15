import asyncio
import base64
import re
from email.message import EmailMessage
from typing import Any, Callable

import httpx
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionTool
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset

from backend.google_auth import google_auth
from backend.permission_store import permission_store
from backend.tools.google_tools.mcp import permission_in_scope


GOOGLE_API = "https://www.googleapis.com"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
DOCS_API = "https://docs.googleapis.com/v1/documents"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
SLIDES_API = "https://slides.googleapis.com/v1/presentations"
CALENDAR_API = "https://www.googleapis.com/calendar/v3"
PEOPLE_API = "https://people.googleapis.com/v1"
GOOGLE_ID = re.compile(r"[-\w]{20,}")


class WorkspaceApiError(RuntimeError):
    pass


class WorkspaceApiToolset(BaseToolset):
    def __init__(self, permission_id: str, functions: list[Callable[..., Any]]) -> None:
        super().__init__()
        self.permission_id = permission_id
        self._tools = [FunctionTool(function) for function in functions]

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        del readonly_context
        if not permission_in_scope(self.permission_id):
            return []
        if not permission_store.enabled(self.permission_id):
            return []
        if not google_auth.snapshot("workspace")["connected"]:
            return []
        return self._tools


async def workspace_request(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any = None,
) -> dict[str, Any]:
    token = await google_auth.access_token("workspace")
    if not token:
        raise WorkspaceApiError("Google Workspace is not connected.")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(
            method,
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            json=json,
        )
    if response.is_error:
        try:
            message = response.json().get("error", {}).get("message")
        except ValueError:
            message = response.text[:500]
        raise WorkspaceApiError(
            f"Google Workspace returned {response.status_code}: "
            f"{message or response.reason_phrase}"
        )
    if not response.content:
        return {}
    return response.json()


async def workspace_gmail_search_threads(query: str, max_results: int = 10) -> dict[str, Any]:
    """Search Gmail and return matching threads with recent message metadata.

    Args:
        query: Gmail search syntax, such as `from:devpost newer_than:1y`.
        max_results: Maximum number of threads to return, from 1 through 25.
    """
    result = await workspace_request(
        "GET",
        f"{GMAIL_API}/threads",
        params={"q": query, "maxResults": max(1, min(25, max_results))},
    )
    thread_ids = [item["id"] for item in result.get("threads", [])]
    details = await asyncio.gather(*(
        workspace_request(
            "GET",
            f"{GMAIL_API}/threads/{thread_id}",
            params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]},
        )
        for thread_id in thread_ids
    ))
    return {"threads": [gmail_thread_summary(thread) for thread in details]}


async def workspace_gmail_get_thread(thread_id: str) -> dict[str, Any]:
    """Read one Gmail thread, including message headers and text bodies."""
    thread = await workspace_request("GET", f"{GMAIL_API}/threads/{thread_id}", params={"format": "full"})
    return {"thread": gmail_thread_summary(thread, include_body=True)}


async def workspace_gmail_get_message(message_id: str) -> dict[str, Any]:
    """Read one Gmail message, including headers and text body."""
    message = await workspace_request("GET", f"{GMAIL_API}/messages/{message_id}", params={"format": "full"})
    return {"message": gmail_message(message, include_body=True)}


async def workspace_gmail_create_draft(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> dict[str, Any]:
    """Create a Gmail draft without sending it.

    Args:
        to: Recipient email addresses.
        subject: Draft subject.
        body: Plain-text message body.
        cc: Optional CC recipients.
        bcc: Optional BCC recipients.
    """
    message = EmailMessage()
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    if bcc:
        message["Bcc"] = ", ".join(bcc)
    message["Subject"] = subject
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
    result = await workspace_request("POST", f"{GMAIL_API}/drafts", json={"message": {"raw": raw}})
    return {"draft_id": result.get("id"), "message_id": result.get("message", {}).get("id")}


async def workspace_gmail_list_labels() -> dict[str, Any]:
    """List Gmail system and user labels."""
    result = await workspace_request("GET", f"{GMAIL_API}/labels")
    return {"labels": result.get("labels", [])}


async def workspace_drive_search_files(query: str, max_results: int = 20) -> dict[str, Any]:
    """Search Google Drive by name or Drive query syntax.

    Args:
        query: A filename phrase or a Drive API query containing operators.
        max_results: Maximum files to return, from 1 through 100.
    """
    drive_query = query if any(operator in query for operator in ("=", " contains ", " in ")) else (
        f"name contains '{query.replace(chr(39), chr(92) + chr(39))}' and trashed = false"
    )
    result = await workspace_request(
        "GET",
        f"{GOOGLE_API}/drive/v3/files",
        params={
            "q": drive_query,
            "pageSize": max(1, min(100, max_results)),
            "orderBy": "modifiedTime desc",
            "fields": "files(id,name,mimeType,modifiedTime,webViewLink,owners(displayName,emailAddress))",
        },
    )
    return {"files": result.get("files", [])}


async def workspace_docs_read_doc(document: str) -> dict[str, Any]:
    """Read a Google Doc by document ID or Docs URL."""
    document_id = google_resource_id(document)
    result = await workspace_request("GET", f"{DOCS_API}/{document_id}")
    return {
        "document_id": document_id,
        "title": result.get("title"),
        "text": document_text(result),
    }


async def workspace_docs_create_doc(title: str, content: str = "") -> dict[str, Any]:
    """Create a Google Doc and optionally insert its initial plain-text content."""
    document = await workspace_request("POST", DOCS_API, json={"title": title})
    document_id = document["documentId"]
    if content:
        await workspace_request(
            "POST",
            f"{DOCS_API}/{document_id}:batchUpdate",
            json={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
        )
    return {
        "document_id": document_id,
        "title": title,
        "url": f"https://docs.google.com/document/d/{document_id}/edit",
    }


async def workspace_docs_append_text(document: str, text: str) -> dict[str, Any]:
    """Append plain text to the end of a Google Doc."""
    document_id = google_resource_id(document)
    current = await workspace_request("GET", f"{DOCS_API}/{document_id}")
    end_index = max(
        1,
        max(
            (element.get("endIndex", 1) for item in current.get("body", {}).get("content", []) for element in item.get("paragraph", {}).get("elements", [])),
            default=1,
        ) - 1,
    )
    await workspace_request(
        "POST",
        f"{DOCS_API}/{document_id}:batchUpdate",
        json={"requests": [{"insertText": {"location": {"index": end_index}, "text": text}}]},
    )
    return {"document_id": document_id, "status": "updated"}


async def workspace_sheets_read_range(spreadsheet: str, range_name: str) -> dict[str, Any]:
    """Read values from a Google Sheets range."""
    spreadsheet_id = google_resource_id(spreadsheet)
    result = await workspace_request("GET", f"{SHEETS_API}/{spreadsheet_id}/values/{range_name}")
    return {"range": result.get("range"), "values": result.get("values", [])}


async def workspace_sheets_update_range(
    spreadsheet: str,
    range_name: str,
    values: list[list[str]],
) -> dict[str, Any]:
    """Write rows of values to a Google Sheets range."""
    spreadsheet_id = google_resource_id(spreadsheet)
    return await workspace_request(
        "PUT",
        f"{SHEETS_API}/{spreadsheet_id}/values/{range_name}",
        params={"valueInputOption": "USER_ENTERED"},
        json={"values": values},
    )


async def workspace_slides_get_presentation(presentation: str) -> dict[str, Any]:
    """Read presentation metadata and slide element text from Google Slides."""
    presentation_id = google_resource_id(presentation)
    result = await workspace_request("GET", f"{SLIDES_API}/{presentation_id}")
    return {
        "presentation_id": presentation_id,
        "title": result.get("title"),
        "slides": [slide_text(slide) for slide in result.get("slides", [])],
    }


async def workspace_calendar_list_events(
    time_min: str,
    time_max: str,
    calendar_id: str = "primary",
    max_results: int = 50,
) -> dict[str, Any]:
    """List Google Calendar events within an RFC3339 time range."""
    result = await workspace_request(
        "GET",
        f"{CALENDAR_API}/calendars/{calendar_id}/events",
        params={
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": max(1, min(250, max_results)),
        },
    )
    return {"events": result.get("items", [])}


async def workspace_calendar_create_event(
    summary: str,
    start: str,
    end: str,
    calendar_id: str = "primary",
    description: str = "",
) -> dict[str, Any]:
    """Create a timed Google Calendar event using RFC3339 start and end values."""
    result = await workspace_request(
        "POST",
        f"{CALENDAR_API}/calendars/{calendar_id}/events",
        json={
            "summary": summary,
            "description": description,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        },
    )
    return {"event_id": result.get("id"), "html_link": result.get("htmlLink")}


async def workspace_people_search_contacts(query: str, max_results: int = 10) -> dict[str, Any]:
    """Search the connected Google account's contacts."""
    result = await workspace_request(
        "GET",
        f"{PEOPLE_API}/people:searchContacts",
        params={
            "query": query,
            "readMask": "names,emailAddresses,phoneNumbers,organizations",
            "pageSize": max(1, min(30, max_results)),
        },
    )
    return {"results": result.get("results", [])}


def create_workspace_toolsets() -> list[WorkspaceApiToolset]:
    return [
        WorkspaceApiToolset("workspace.gmail", [
            workspace_gmail_search_threads,
            workspace_gmail_get_thread,
            workspace_gmail_get_message,
            workspace_gmail_create_draft,
            workspace_gmail_list_labels,
        ]),
        WorkspaceApiToolset("workspace.drive", [workspace_drive_search_files]),
        WorkspaceApiToolset("workspace.docs", [
            workspace_docs_read_doc,
            workspace_docs_create_doc,
            workspace_docs_append_text,
        ]),
        WorkspaceApiToolset("workspace.sheets", [
            workspace_sheets_read_range,
            workspace_sheets_update_range,
        ]),
        WorkspaceApiToolset("workspace.slides", [workspace_slides_get_presentation]),
        WorkspaceApiToolset("workspace.calendar", [
            workspace_calendar_list_events,
            workspace_calendar_create_event,
        ]),
        WorkspaceApiToolset("workspace.people", [workspace_people_search_contacts]),
    ]


def google_resource_id(value: str) -> str:
    if "/d/" in value:
        value = value.split("/d/", 1)[1].split("/", 1)[0]
    match = GOOGLE_ID.fullmatch(value.strip())
    if not match:
        raise WorkspaceApiError("A valid Google resource ID or URL is required.")
    return match.group(0)


def gmail_thread_summary(thread: dict[str, Any], include_body: bool = False) -> dict[str, Any]:
    return {
        "id": thread.get("id"),
        "history_id": thread.get("historyId"),
        "messages": [gmail_message(message, include_body) for message in thread.get("messages", [])],
    }


def gmail_message(message: dict[str, Any], include_body: bool = False) -> dict[str, Any]:
    headers = {
        header.get("name", "").casefold(): header.get("value", "")
        for header in message.get("payload", {}).get("headers", [])
    }
    result = {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "from": headers.get("from"),
        "to": headers.get("to"),
        "subject": headers.get("subject"),
        "date": headers.get("date"),
        "snippet": message.get("snippet"),
    }
    if include_body:
        result["body"] = gmail_body(message.get("payload", {}))
    return result


def gmail_body(payload: dict[str, Any]) -> str:
    body = payload.get("body", {}).get("data")
    if body and payload.get("mimeType") == "text/plain":
        return decode_base64(body)
    for part in payload.get("parts", []):
        text = gmail_body(part)
        if text:
            return text
    return decode_base64(body) if body else ""


def decode_base64(value: str) -> str:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode(errors="replace")


def document_text(document: dict[str, Any]) -> str:
    return "".join(
        run.get("textRun", {}).get("content", "")
        for item in document.get("body", {}).get("content", [])
        for run in item.get("paragraph", {}).get("elements", [])
    )


def slide_text(slide: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_id": slide.get("objectId"),
        "text": "".join(
            run.get("textRun", {}).get("content", "")
            for element in slide.get("pageElements", [])
            for run in element.get("shape", {}).get("text", {}).get("textElements", [])
        ),
    }
