import os
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

from backend.runtime_paths import playwright_mcp_binary

PLAYWRIGHT_MCP_BINARY = playwright_mcp_binary()

BROWSER_TOOL_NAMES = [
    "browser_navigate",
    "browser_navigate_back",
    "browser_snapshot",
    "browser_find",
    "browser_click",
    "browser_type",
    "browser_fill_form",
    "browser_select_option",
    "browser_press_key",
    "browser_hover",
    "browser_drag",
    "browser_handle_dialog",
    "browser_file_upload",
    "browser_tabs",
    "browser_wait_for",
    "browser_evaluate",
]


def create_playwright_toolset() -> McpToolset:
    if not PLAYWRIGHT_MCP_BINARY.is_file():
        raise RuntimeError(
            "Playwright MCP is not installed. Run `pnpm install` from the Sherpa root."
        )

    environment = dict(os.environ)
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=str(PLAYWRIGHT_MCP_BINARY),
                args=[
                    "--extension",
                    "--browser",
                    "chrome",
                    "--snapshot-boxes",
                    "--image-responses",
                    "omit",
                    "--codegen",
                    "none",
                    "--timeout-action",
                    "8000",
                    "--timeout-navigation",
                    "30000",
                    "--timeout-settle",
                    "250",
                ],
                env=environment,
            ),
            timeout=30,
        ),
        tool_filter=BROWSER_TOOL_NAMES,
        use_mcp_resources=False,
    )
