import logging
from typing import Any

from google.adk.tools import BaseTool, ToolContext

from backend.permission_store import permission_store
from backend.tools.computer_use.runtime import computer_runtime


logger = logging.getLogger("sherpa.computer_use")
MAX_TOOL_TEXT = 40_000


async def before_computer_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, str] | None:
    logger.info(
        "tool.started session=%s call=%s name=%s",
        tool_context.session.id,
        tool_context.function_call_id,
        tool.name,
    )
    required_permission = tool_permission(tool.name)
    if required_permission and not permission_store.enabled(required_permission):
        return {
            "status": "failed",
            "error": f"{required_permission} is turned off in Sherpa Plugins.",
        }
    app_target = next((
        args.get(key)
        for key in ("app", "app_target", "bundle_id")
        if isinstance(args.get(key), str)
    ), None)
    if app_target and not permission_store.app_enabled(app_target):
        return {
            "status": "failed",
            "error": f"Access to {app_target} is turned off in Sherpa Plugins.",
        }
    mode = await computer_runtime.acquire(
        tool_call_key(tool, tool_context),
        tool.name,
        args,
    )
    del mode
    return None


async def after_computer_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict,
) -> dict:
    del args
    computer_runtime.release(tool_call_key(tool, tool_context))
    safe_response = sanitize_tool_response(tool_response)
    if safe_response.get("isError") or safe_response.get("error"):
        logger.warning(
            "tool.failed session=%s call=%s name=%s",
            tool_context.session.id,
            tool_context.function_call_id,
            tool.name,
        )
    else:
        logger.debug(
            "tool.completed session=%s call=%s name=%s",
            tool_context.session.id,
            tool_context.function_call_id,
            tool.name,
        )
    return safe_response


async def on_computer_tool_error(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> dict[str, str]:
    del args
    computer_runtime.release(tool_call_key(tool, tool_context))
    logger.error(
        "tool.failed session=%s call=%s name=%s error=%s",
        tool_context.session.id,
        tool_context.function_call_id,
        tool.name,
        error,
    )
    return {
        "status": "failed",
        "error": f"{tool.name} failed: {error}",
    }


def sanitize_tool_response(response: dict) -> dict:
    safe = dict(response)
    content = safe.get("content")
    if isinstance(content, list):
        text_blocks = []
        omitted_images = 0
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                text_blocks.append(
                    {"type": "text", "text": block["text"][:MAX_TOOL_TEXT]}
                )
            elif block.get("type") in {"image", "audio"}:
                omitted_images += 1
        safe["content"] = text_blocks
        if omitted_images:
            safe["media_omitted"] = omitted_images
    safe.pop("_meta", None)
    safe.pop("meta", None)
    return safe


def tool_call_key(tool: BaseTool, tool_context: ToolContext) -> str:
    return tool_context.function_call_id or f"{tool_context.session.id}:{tool.name}"


def tool_permission(tool_name: str) -> str | None:
    for product in ("drive", "docs", "sheets", "slides", "gmail", "calendar", "people"):
        if tool_name.startswith(f"workspace_{product}_"):
            return f"workspace.{product}"
    if tool_name.startswith("cloud_resources_"):
        return "cloud.resources"
    if tool_name.startswith("cloud_cli_"):
        return "cloud.cli"
    if tool_name in {"browser_snapshot", "browser_find"}:
        return "browser.read"
    if tool_name == "browser_tabs":
        return "browser.tabs"
    if tool_name.startswith("browser_"):
        return "browser.interact"
    if tool_name in {"computer_see", "computer_inspect_ui"}:
        return "mac.screen"
    if tool_name.startswith("computer_"):
        return "mac.control"
    return None
