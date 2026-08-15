import asyncio
import os
import logging
from contextlib import suppress
from contextvars import ContextVar
from collections.abc import AsyncIterator
from typing import Any

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

from backend.google_auth import GoogleConnection, google_auth
from backend.permission_store import permission_store


logger = logging.getLogger("sherpa.google_tools")
_active_permissions: ContextVar[frozenset[str] | None] = ContextVar(
    "sherpa_google_tool_permissions",
    default=None,
)


class ConnectedGoogleMcpToolset(BaseToolset):
    """Expose a Google remote MCP server only after its user connection exists."""

    def __init__(
        self,
        *,
        connection: GoogleConnection,
        endpoint: str,
        permission_id: str,
        prefix: str,
    ) -> None:
        super().__init__()
        self.connection = connection
        self.endpoint = endpoint
        self.permission_id = permission_id
        self.prefix = prefix
        self._token: str | None = None
        self._delegate: McpToolset | None = None
        self._tools: list[BaseTool] | None = None
        self._failed_token: str | None = None
        self._catalog_lock = asyncio.Lock()

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        del readonly_context
        active_permissions = _active_permissions.get()
        if active_permissions is not None and self.permission_id not in active_permissions:
            return []
        if not permission_store.enabled(self.permission_id):
            return []
        token = await google_auth.access_token(self.connection)
        if not token:
            return []
        if token == self._failed_token:
            return []
        async with self._catalog_lock:
            if token != self._token or not self._delegate:
                if self._delegate:
                    await self._delegate.close()
                self._delegate = McpToolset(
                    connection_params=StreamableHTTPConnectionParams(
                        url=self.endpoint,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "x-goog-user-project": os.getenv(
                                "GOOGLE_CLOUD_PROJECT",
                                "sherpa-20260813",
                            ),
                        },
                        timeout=15,
                    ),
                    tool_name_prefix=self.prefix,
                )
                self._token = token
                self._tools = None
                self._failed_token = None
            if self._tools is not None:
                return self._tools
            try:
                self._tools = await self._delegate.get_tools_with_prefix()
            except Exception as error:
                self._failed_token = token
                with suppress(Exception):
                    await self._delegate.close()
                self._delegate = None
                logger.warning(
                    "toolset.unavailable permission=%s error=%s",
                    self.permission_id,
                    error,
                )
                return []
            return self._tools

    async def close(self) -> None:
        if self._delegate:
            await self._delegate.close()
        self._delegate = None
        self._token = None
        self._tools = None
        self._failed_token = None


async def run_with_google_tool_scope(
    runner: Any,
    instruction: str,
    **run_arguments: Any,
) -> AsyncIterator[Any]:
    permissions = infer_google_permissions(instruction)
    events = runner.run_async(**run_arguments).__aiter__()
    while True:
        token = _active_permissions.set(permissions)
        try:
            event = await anext(events)
        except StopAsyncIteration:
            return
        finally:
            _active_permissions.reset(token)
        yield event


def infer_google_permissions(instruction: str) -> frozenset[str]:
    text = instruction.casefold()
    permissions: set[str] = set()
    keyword_groups = {
        "workspace.drive": ("google drive", "drive file", "drive folder"),
        "workspace.docs": ("google doc", "google docs", "document in drive"),
        "workspace.sheets": ("google sheet", "spreadsheet"),
        "workspace.slides": ("google slide", "presentation in drive"),
        "workspace.gmail": ("gmail", "email", "inbox", "mailbox"),
        "workspace.calendar": ("google calendar", "calendar", "meeting", "schedule"),
        "workspace.people": ("google contact", "contacts", "address book"),
        "cloud.resources": ("google cloud", "gcp", "cloud project", "cloud resource"),
        "cloud.cli": ("gcloud", "cloud cli", "google cloud command"),
    }
    for permission, keywords in keyword_groups.items():
        if any(keyword in text for keyword in keywords):
            permissions.add(permission)
    if "google workspace" in text:
        permissions.update(permission for permission in keyword_groups if permission.startswith("workspace."))
    return frozenset(permissions)


def create_google_toolsets() -> list[ConnectedGoogleMcpToolset]:
    workspace = (
        ("drive", "https://drivemcp.googleapis.com/mcp/v1"),
        ("docs", "https://docsmcp.googleapis.com/mcp/v1"),
        ("sheets", "https://sheetsmcp.googleapis.com/mcp/v1"),
        ("slides", "https://slidesmcp.googleapis.com/mcp/v1"),
        ("gmail", "https://gmailmcp.googleapis.com/mcp/v1"),
        ("calendar", "https://calendarmcp.googleapis.com/mcp/v1"),
        ("people", "https://people.googleapis.com/mcp/v1"),
    )
    toolsets = [
        ConnectedGoogleMcpToolset(
            connection="workspace",
            endpoint=endpoint,
            permission_id=f"workspace.{product}",
            prefix=f"workspace_{product}",
        )
        for product, endpoint in workspace
    ]
    toolsets.extend((
        ConnectedGoogleMcpToolset(
            connection="workspace",
            endpoint="https://cloudresourcemanager.googleapis.com/mcp",
            permission_id="cloud.resources",
            prefix="cloud_resources",
        ),
        ConnectedGoogleMcpToolset(
            connection="workspace",
            endpoint="https://cloudcli.googleapis.com/mcp",
            permission_id="cloud.cli",
            prefix="cloud_cli",
        ),
    ))
    return toolsets
