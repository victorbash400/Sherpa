import base64
import asyncio
import html
import re
from email.message import EmailMessage
from email.utils import getaddresses, parseaddr
from typing import Any

from backend.tools.google_tools.workspace_core import WorkspaceApiError, workspace_request


GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


def _header(message: dict[str, Any], name: str) -> str:
    return next((
        str(item.get("value", ""))
        for item in message.get("payload", {}).get("headers", [])
        if str(item.get("name", "")).casefold() == name.casefold()
    ), "")


def _encoded_message(
    *,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html_body: str | None = None,
    attachments: list[dict[str, str]] | None = None,
    reply_to_message_id: str | None = None,
    references: str | None = None,
) -> str:
    message = EmailMessage()
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    if bcc:
        message["Bcc"] = ", ".join(bcc)
    message["Subject"] = subject
    if reply_to_message_id:
        message["In-Reply-To"] = reply_to_message_id
    if references:
        message["References"] = references
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    for attachment in attachments or []:
        filename = attachment.get("filename", "attachment")
        mime_type = attachment.get("mime_type", "application/octet-stream")
        if "/" not in mime_type:
            raise WorkspaceApiError(f"Invalid attachment MIME type: {mime_type}")
        try:
            data = base64.b64decode(attachment["data_base64"], validate=True)
        except (KeyError, ValueError) as error:
            raise WorkspaceApiError(f"Attachment {filename} has invalid base64 data.") from error
        main_type, sub_type = mime_type.split("/", 1)
        message.add_attachment(data, maintype=main_type, subtype=sub_type, filename=filename)
    return base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")


def _decoded_body(payload: dict[str, Any]) -> str:
    data = payload.get("body", {}).get("data")
    if data and payload.get("mimeType") in {"text/plain", "text/html"}:
        decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(errors="replace")
        if payload.get("mimeType") == "text/html":
            return html.unescape(re.sub(r"<[^>]+>", " ", decoded))
        return decoded
    children = payload.get("parts", [])
    plain = next((text for part in children if part.get("mimeType") == "text/plain" and (text := _decoded_body(part))), "")
    return plain or next((text for part in children if (text := _decoded_body(part))), "")


def _attachment_parts(payload: dict[str, Any]) -> list[dict[str, str]]:
    parts: list[dict[str, str]] = []
    attachment_id = payload.get("body", {}).get("attachmentId")
    if attachment_id and payload.get("filename"):
        parts.append({
            "attachment_id": attachment_id,
            "filename": payload["filename"],
            "mime_type": payload.get("mimeType", "application/octet-stream"),
        })
    for child in payload.get("parts", []):
        parts.extend(_attachment_parts(child))
    return parts


async def workspace_gmail_send_rich_message(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html_body: str | None = None,
    attachments: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Send an email with optional HTML and base64-encoded file attachments."""
    raw = _encoded_message(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html_body=html_body,
        attachments=attachments,
    )
    result = await workspace_request("POST", f"{GMAIL_API}/messages/send", json={"raw": raw})
    return {"message_id": result.get("id"), "thread_id": result.get("threadId"), "status": "sent"}


async def workspace_gmail_create_rich_draft(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html_body: str | None = None,
    attachments: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Create a Gmail draft with optional HTML and base64-encoded attachments."""
    raw = _encoded_message(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html_body=html_body,
        attachments=attachments,
    )
    result = await workspace_request("POST", f"{GMAIL_API}/drafts", json={"message": {"raw": raw}})
    return {"draft_id": result.get("id"), "message_id": result.get("message", {}).get("id")}


async def workspace_gmail_reply(
    message_id: str,
    body: str,
    reply_all: bool = False,
    html_body: str | None = None,
    attachments: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Reply to a Gmail message while preserving its thread."""
    original = await workspace_request(
        "GET",
        f"{GMAIL_API}/messages/{message_id}",
        params={"format": "metadata", "metadataHeaders": ["From", "Reply-To", "To", "Cc", "Subject", "Message-ID", "References"]},
    )
    sender = parseaddr(_header(original, "Reply-To") or _header(original, "From"))[1]
    if not sender:
        raise WorkspaceApiError("The original message does not contain a reply address.")
    recipients = [sender]
    cc = None
    if reply_all:
        profile = await workspace_request("GET", f"{GMAIL_API}/profile")
        own_address = str(profile.get("emailAddress", "")).casefold()
        other_addresses = [
            address
            for _, address in getaddresses([_header(original, "To"), _header(original, "Cc")])
            if address and address.casefold() not in {own_address, sender.casefold()}
        ]
        cc = list(dict.fromkeys(other_addresses)) or None
    subject = _header(original, "Subject")
    if not subject.casefold().startswith("re:"):
        subject = f"Re: {subject}"
    original_message_id = _header(original, "Message-ID")
    references = " ".join(filter(None, [_header(original, "References"), original_message_id]))
    raw = _encoded_message(
        to=list(dict.fromkeys(recipients)),
        subject=subject,
        body=body,
        cc=cc,
        html_body=html_body,
        attachments=attachments,
        reply_to_message_id=original_message_id or None,
        references=references or None,
    )
    result = await workspace_request(
        "POST",
        f"{GMAIL_API}/messages/send",
        json={"raw": raw, "threadId": original.get("threadId")},
    )
    return {"message_id": result.get("id"), "thread_id": result.get("threadId"), "status": "sent"}


async def workspace_gmail_forward(
    message_id: str,
    to: list[str],
    body_intro: str = "",
) -> dict[str, Any]:
    """Forward a Gmail message and its file attachments to new recipients."""
    original = await workspace_request("GET", f"{GMAIL_API}/messages/{message_id}", params={"format": "full"})
    payload = original.get("payload", {})
    attachment_parts = _attachment_parts(payload)
    attachment_results = await asyncio.gather(*(
        workspace_request("GET", f"{GMAIL_API}/messages/{message_id}/attachments/{part['attachment_id']}")
        for part in attachment_parts
    ))
    attachments = [
        {
            "filename": part["filename"],
            "mime_type": part["mime_type"],
            "data_base64": result.get("data", "").replace("-", "+").replace("_", "/") + "=" * (-len(result.get("data", "")) % 4),
        }
        for part, result in zip(attachment_parts, attachment_results, strict=True)
    ]
    subject = _header(original, "Subject")
    if not subject.casefold().startswith("fwd:"):
        subject = f"Fwd: {subject}"
    forwarded_header = (
        "---------- Forwarded message ---------\n"
        f"From: {_header(original, 'From')}\n"
        f"Date: {_header(original, 'Date')}\n"
        f"Subject: {_header(original, 'Subject')}\n"
        f"To: {_header(original, 'To')}\n\n"
    )
    body = f"{body_intro.rstrip()}\n\n" if body_intro else ""
    body += forwarded_header + _decoded_body(payload)
    raw = _encoded_message(to=to, subject=subject, body=body, attachments=attachments)
    result = await workspace_request("POST", f"{GMAIL_API}/messages/send", json={"raw": raw})
    return {"message_id": result.get("id"), "thread_id": result.get("threadId"), "status": "sent"}


async def workspace_gmail_modify_message(
    message_id: str,
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Apply Gmail labels or state changes such as read, unread, starred, or archived."""
    if not add_label_ids and not remove_label_ids:
        raise WorkspaceApiError("Provide at least one label to add or remove.")
    result = await workspace_request(
        "POST",
        f"{GMAIL_API}/messages/{message_id}/modify",
        json={"addLabelIds": add_label_ids or [], "removeLabelIds": remove_label_ids or []},
    )
    return {"message_id": result.get("id"), "label_ids": result.get("labelIds", []), "status": "updated"}


async def workspace_gmail_trash_message(message_id: str, trashed: bool = True) -> dict[str, Any]:
    """Move a Gmail message to trash or restore it from trash."""
    action = "trash" if trashed else "untrash"
    result = await workspace_request("POST", f"{GMAIL_API}/messages/{message_id}/{action}")
    return {"message_id": result.get("id"), "thread_id": result.get("threadId"), "trashed": trashed}


async def workspace_gmail_create_label(name: str) -> dict[str, Any]:
    """Create a Gmail label."""
    result = await workspace_request(
        "POST",
        f"{GMAIL_API}/labels",
        json={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
    )
    return {"label_id": result.get("id"), "name": result.get("name")}


async def workspace_gmail_get_attachment(
    message_id: str,
    attachment_id: str,
) -> dict[str, Any]:
    """Download one Gmail attachment as URL-safe base64 data."""
    result = await workspace_request(
        "GET",
        f"{GMAIL_API}/messages/{message_id}/attachments/{attachment_id}",
    )
    return {"attachment_id": attachment_id, "size": result.get("size"), "data_base64": result.get("data")}


GMAIL_EXTRA_TOOLS = [
    workspace_gmail_send_rich_message,
    workspace_gmail_create_rich_draft,
    workspace_gmail_reply,
    workspace_gmail_forward,
    workspace_gmail_modify_message,
    workspace_gmail_trash_message,
    workspace_gmail_create_label,
    workspace_gmail_get_attachment,
]
