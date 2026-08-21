from pathlib import Path

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PEEKABOO_BINARY = (
    PROJECT_ROOT
    / "peekaboo-sherpa"
    / "Apps"
    / "CLI"
    / ".build"
    / "release"
    / "peekaboo"
)

PEEKABOO_TOOL_NAMES = [
    "inspect_ui",
    "app",
    "surfaces",
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
    "inspect_ui",
    "app",
    "click",
    "type",
    "press",
    "scroll",
    "set_value",
    "action",
]


class NoTimeoutStdioConnectionParams(StdioConnectionParams):
    timeout: float | None = None


def create_peekaboo_toolset(
    tool_names: list[str] | None = None,
) -> McpToolset:
    if not PEEKABOO_BINARY.is_file():
        raise RuntimeError(
            "Sherpa's Peekaboo fork is not built. Run "
            "`swift build --configuration release --package-path Apps/CLI` "
            "from the repository's `peekaboo-sherpa` directory."
        )

    return McpToolset(
        connection_params=NoTimeoutStdioConnectionParams(
            server_params=StdioServerParameters(
                command=str(PEEKABOO_BINARY),
                args=["mcp", "--log-level", "warning"],
            ),
        ),
        tool_filter=tool_names or PEEKABOO_TOOL_NAMES,
        tool_name_prefix="computer",
        use_mcp_resources=False,
    )
