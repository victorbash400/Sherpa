import re
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


async def workspace_response(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any = None,
    content: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    token = await google_auth.access_token("workspace")
    if not token:
        raise WorkspaceApiError("Google Workspace is not connected.")
    request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(
            method,
            url,
            headers=request_headers,
            params=params,
            json=json,
            content=content,
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
    return response


async def workspace_request(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any = None,
) -> dict[str, Any]:
    response = await workspace_response(method, url, params=params, json=json)
    if not response.content:
        return {}
    return response.json()


def google_resource_id(value: str) -> str:
    if "/d/" in value:
        value = value.split("/d/", 1)[1].split("/", 1)[0]
    match = GOOGLE_ID.fullmatch(value.strip())
    if not match:
        raise WorkspaceApiError("A valid Google resource ID or URL is required.")
    return match.group(0)


def workspace_preview(
    resource_id: str,
    title: str | None = None,
    mime_type: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": "workspace",
        "resource_id": resource_id,
        "title": title,
        "mime_type": mime_type,
    }
