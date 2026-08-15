import os

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

from backend.google_auth import GoogleConnection, google_auth
from backend.permission_store import permission_store


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

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        del readonly_context
        if not permission_store.enabled(self.permission_id):
            return []
        token = await google_auth.access_token(self.connection)
        if not token:
            return []
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
        return await self._delegate.get_tools_with_prefix()

    async def close(self) -> None:
        if self._delegate:
            await self._delegate.close()
        self._delegate = None
        self._token = None


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
