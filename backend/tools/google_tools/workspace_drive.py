import base64
import json
import secrets
from typing import Any

from backend.tools.google_tools.workspace_core import (
    GOOGLE_API,
    WorkspaceApiError,
    google_resource_id,
    workspace_request,
    workspace_response,
)


DRIVE_API = f"{GOOGLE_API}/drive/v3"
DRIVE_UPLOAD_API = f"{GOOGLE_API}/upload/drive/v3"


async def workspace_drive_list_folder(folder: str = "root", max_results: int = 100) -> dict[str, Any]:
    """List files directly inside a Drive folder."""
    folder_id = folder if folder == "root" else google_resource_id(folder)
    result = await workspace_request(
        "GET",
        f"{DRIVE_API}/files",
        params={
            "q": f"'{folder_id}' in parents and trashed = false",
            "pageSize": max(1, min(100, max_results)),
            "orderBy": "folder,name",
            "fields": "files(id,name,mimeType,modifiedTime,webViewLink,parents,size)",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        },
    )
    return {"files": result.get("files", [])}


async def workspace_drive_upload_file(
    name: str,
    data_base64: str,
    mime_type: str = "application/octet-stream",
    parent_id: str | None = None,
) -> dict[str, Any]:
    """Upload a base64-encoded file to Google Drive."""
    try:
        data = base64.b64decode(data_base64, validate=True)
    except ValueError as error:
        raise WorkspaceApiError("The uploaded file has invalid base64 data.") from error
    metadata: dict[str, Any] = {"name": name}
    if parent_id:
        metadata["parents"] = [google_resource_id(parent_id)]
    boundary = f"sherpa-{secrets.token_hex(12)}"
    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    response = await workspace_response(
        "POST",
        f"{DRIVE_UPLOAD_API}/files",
        params={"uploadType": "multipart", "fields": "id,name,mimeType,size,webViewLink,parents"},
        content=body,
        headers={"Content-Type": f"multipart/related; boundary={boundary}"},
    )
    return response.json()


async def workspace_drive_download_file(file: str) -> dict[str, Any]:
    """Download a binary Drive file as base64 data."""
    file_id = google_resource_id(file)
    metadata = await workspace_request(
        "GET",
        f"{DRIVE_API}/files/{file_id}",
        params={"fields": "id,name,mimeType,size", "supportsAllDrives": "true"},
    )
    if str(metadata.get("mimeType", "")).startswith("application/vnd.google-apps."):
        raise WorkspaceApiError("Google Workspace files must be exported to a requested format.")
    response = await workspace_response(
        "GET",
        f"{DRIVE_API}/files/{file_id}",
        params={"alt": "media", "supportsAllDrives": "true"},
    )
    return {
        **metadata,
        "data_base64": base64.b64encode(response.content).decode(),
    }


async def workspace_drive_export_file(file: str, mime_type: str) -> dict[str, Any]:
    """Export a Google Doc, Sheet, or Slides file as base64 data."""
    file_id = google_resource_id(file)
    response = await workspace_response(
        "GET",
        f"{DRIVE_API}/files/{file_id}/export",
        params={"mimeType": mime_type},
    )
    return {
        "file_id": file_id,
        "mime_type": mime_type,
        "size": len(response.content),
        "data_base64": base64.b64encode(response.content).decode(),
    }


async def workspace_drive_copy_file(
    file: str,
    name: str | None = None,
    parent_id: str | None = None,
) -> dict[str, Any]:
    """Copy a Drive file, optionally renaming or placing it in a folder."""
    payload: dict[str, Any] = {}
    if name:
        payload["name"] = name
    if parent_id:
        payload["parents"] = [google_resource_id(parent_id)]
    return await workspace_request(
        "POST",
        f"{DRIVE_API}/files/{google_resource_id(file)}/copy",
        params={"fields": "id,name,mimeType,webViewLink,parents", "supportsAllDrives": "true"},
        json=payload,
    )


async def workspace_drive_move_file(file: str, folder: str) -> dict[str, Any]:
    """Move a Drive file into a different folder."""
    file_id = google_resource_id(file)
    folder_id = google_resource_id(folder)
    current = await workspace_request(
        "GET",
        f"{DRIVE_API}/files/{file_id}",
        params={"fields": "parents", "supportsAllDrives": "true"},
    )
    return await workspace_request(
        "PATCH",
        f"{DRIVE_API}/files/{file_id}",
        params={
            "addParents": folder_id,
            "removeParents": ",".join(current.get("parents", [])),
            "fields": "id,name,mimeType,webViewLink,parents",
            "supportsAllDrives": "true",
        },
        json={},
    )


async def workspace_drive_list_permissions(file: str) -> dict[str, Any]:
    """List sharing permissions for a Drive file."""
    result = await workspace_request(
        "GET",
        f"{DRIVE_API}/files/{google_resource_id(file)}/permissions",
        params={"fields": "permissions(id,type,role,emailAddress,displayName,domain,expirationTime)", "supportsAllDrives": "true"},
    )
    return {"permissions": result.get("permissions", [])}


async def workspace_drive_share_file(
    file: str,
    role: str,
    email: str | None = None,
    permission_type: str = "user",
    send_notification: bool = True,
) -> dict[str, Any]:
    """Share a Drive file with a user, group, domain, or anyone."""
    if role not in {"reader", "commenter", "writer"}:
        raise WorkspaceApiError("Role must be reader, commenter, or writer.")
    if permission_type not in {"user", "group", "domain", "anyone"}:
        raise WorkspaceApiError("Unsupported Drive permission type.")
    payload: dict[str, Any] = {"type": permission_type, "role": role}
    if permission_type in {"user", "group"}:
        if not email:
            raise WorkspaceApiError("An email address is required for user or group sharing.")
        payload["emailAddress"] = email
    elif permission_type == "domain":
        if not email:
            raise WorkspaceApiError("A domain is required for domain sharing.")
        payload["domain"] = email
    result = await workspace_request(
        "POST",
        f"{DRIVE_API}/files/{google_resource_id(file)}/permissions",
        params={
            "sendNotificationEmail": str(send_notification).lower(),
            "fields": "id,type,role,emailAddress,displayName,domain",
            "supportsAllDrives": "true",
        },
        json=payload,
    )
    return {"permission": result}


async def workspace_drive_list_comments(file: str) -> dict[str, Any]:
    """List comments and replies on a Drive file."""
    result = await workspace_request(
        "GET",
        f"{DRIVE_API}/files/{google_resource_id(file)}/comments",
        params={"fields": "comments(id,content,quotedFileContent,resolved,createdTime,modifiedTime,author(displayName,emailAddress),replies)"},
    )
    return {"comments": result.get("comments", [])}


async def workspace_drive_create_comment(file: str, content: str) -> dict[str, Any]:
    """Create a comment on a Drive file."""
    result = await workspace_request(
        "POST",
        f"{DRIVE_API}/files/{google_resource_id(file)}/comments",
        params={"fields": "id,content,createdTime,resolved,author(displayName,emailAddress)"},
        json={"content": content},
    )
    return {"comment": result}


async def workspace_drive_reply_to_comment(file: str, comment_id: str, content: str) -> dict[str, Any]:
    """Reply to a Drive file comment."""
    result = await workspace_request(
        "POST",
        f"{DRIVE_API}/files/{google_resource_id(file)}/comments/{comment_id}/replies",
        params={"fields": "id,content,createdTime,author(displayName,emailAddress)"},
        json={"content": content},
    )
    return {"reply": result}


DRIVE_EXTRA_TOOLS = [
    workspace_drive_list_folder,
    workspace_drive_upload_file,
    workspace_drive_download_file,
    workspace_drive_export_file,
    workspace_drive_copy_file,
    workspace_drive_move_file,
    workspace_drive_list_permissions,
    workspace_drive_share_file,
    workspace_drive_list_comments,
    workspace_drive_create_comment,
    workspace_drive_reply_to_comment,
]
