import json
import logging
from typing import Any

from google.adk.tools import BaseTool, ToolContext


logger = logging.getLogger("sherpa.computer_use")
MAX_TOOL_TEXT = 40_000


def before_computer_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> None:
    logger.info(
        "tool.start session=%s call=%s name=%s args=%s",
        tool_context.session.id,
        tool_context.function_call_id,
        tool.name,
        json.dumps(args, default=str),
    )


def after_computer_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict,
) -> dict:
    del args
    safe_response = sanitize_tool_response(tool_response)
    logger.info(
        "tool.finish session=%s call=%s name=%s raw_bytes=%d safe_bytes=%d error=%s",
        tool_context.session.id,
        tool_context.function_call_id,
        tool.name,
        len(json.dumps(tool_response, default=str)),
        len(json.dumps(safe_response, default=str)),
        bool(safe_response.get("isError") or safe_response.get("error")),
    )
    return safe_response


def on_computer_tool_error(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> dict[str, str]:
    logger.exception(
        "tool.failed session=%s call=%s name=%s args=%s",
        tool_context.session.id,
        tool_context.function_call_id,
        tool.name,
        json.dumps(args, default=str),
        exc_info=error,
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
