from pathlib import Path

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PEEKABOO_BINARY = PROJECT_ROOT / "node_modules" / ".bin" / "peekaboo"

PEEKABOO_TOOL_NAMES = [
    "see",
    "inspect_ui",
    "permissions",
    "app",
    "window",
    "menu",
    "dialog",
    "click",
    "type",
    "press",
    "scroll",
    "drag",
    "set_value",
    "action",
]

PEEKABOO_VOICE_TOOL_NAMES = [
    "see",
    "inspect_ui",
    "app",
    "click",
    "type",
    "press",
    "scroll",
    "set_value",
    "action",
]


def create_peekaboo_toolset(
    tool_names: list[str] | None = None,
) -> McpToolset:
    if not PEEKABOO_BINARY.is_file():
        raise RuntimeError(
            "Peekaboo is not installed. Run `pnpm install` from the Sherpa root."
        )

    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=str(PEEKABOO_BINARY),
                args=["mcp", "--log-level", "warning"],
            ),
            timeout=30,
        ),
        tool_filter=tool_names or PEEKABOO_TOOL_NAMES,
        tool_name_prefix="computer",
        use_mcp_resources=False,
    )
