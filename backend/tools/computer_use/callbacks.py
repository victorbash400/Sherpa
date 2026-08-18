import logging
import re
import time
from pathlib import Path
from typing import Any

from google.adk.tools import BaseTool, ToolContext

from backend.permission_store import permission_store
from backend.tools.computer_use.runtime import computer_runtime, is_interaction_tool


logger = logging.getLogger("sherpa.computer_use")
BROWSER_EVALUATE_FORBIDDEN = re.compile(
    r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|eval|Function|import|"
    r"localStorage|sessionStorage|indexedDB)\b|"
    r"document\s*\.\s*cookie|navigator\s*\.\s*(?:clipboard|credentials)|"
    r"window\s*\.\s*(?:open|location)|location\s*\.|history\s*\.|"
    r"requestSubmit\s*\(|\.submit\s*\(",
    re.IGNORECASE,
)
COMPOUND_PID_TARGET = re.compile(r"^pid\s*:\s*(\d+)(?::(.*))?$", re.IGNORECASE)
tool_started_at: dict[str, float] = {}


async def before_computer_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> dict[str, str] | None:
    validation_error = normalize_tool_args(tool.name, args)
    if validation_error:
        logger.warning(
            "tool.rejected session=%s call=%s name=%s error=%s",
            tool_context.session.id,
            tool_context.function_call_id,
            tool.name,
            validation_error,
        )
        return {"status": "failed", "error": validation_error}
    key = tool_call_key(tool, tool_context)
    tool_started_at[key] = time.perf_counter()
    logger.info(
        "tool.start session=%s call=%s name=%s target=%s",
        tool_context.session.id,
        tool_context.function_call_id,
        tool.name,
        tool_target(args),
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
    if app_target is None and isinstance(args.get("pid"), int):
        app_target = f"PID:{args['pid']}"
    if (
        app_target
        and app_target.casefold() != "frontmost"
        and not permission_store.app_enabled(app_target)
    ):
        return {
            "status": "failed",
            "error": f"Access to {app_target} is turned off in Sherpa Plugins.",
        }
    if is_interaction_tool(tool.name):
        await computer_runtime.acquire(
            tool_call_key(tool, tool_context),
            tool.name,
            args,
        )
    return None


async def after_computer_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict,
) -> dict:
    duration_ms = tool_duration_ms(tool, tool_context)
    if is_interaction_tool(tool.name):
        computer_runtime.release(tool_call_key(tool, tool_context))
    safe_response = normalize_tool_outcome(
        tool.name,
        args,
        sanitize_tool_response(tool_response, tool.name),
    )
    if (
        safe_response.get("isError")
        or safe_response.get("error")
        or safe_response.get("status") == "failed"
    ):
        logger.warning(
            "tool.failed session=%s call=%s name=%s duration_ms=%d error=%s",
            tool_context.session.id,
            tool_context.function_call_id,
            tool.name,
            duration_ms,
            response_error(safe_response),
        )
    else:
        logger.info(
            "tool.done session=%s call=%s name=%s duration_ms=%d",
            tool_context.session.id,
            tool_context.function_call_id,
            tool.name,
            duration_ms,
        )
    return safe_response


async def on_computer_tool_error(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    error: Exception,
) -> dict[str, str]:
    del args
    duration_ms = tool_duration_ms(tool, tool_context)
    if is_interaction_tool(tool.name):
        computer_runtime.release(tool_call_key(tool, tool_context))
    logger.error(
        "tool.failed session=%s call=%s name=%s duration_ms=%d error=%s",
        tool_context.session.id,
        tool_context.function_call_id,
        tool.name,
        duration_ms,
        error,
    )
    return {
        "status": "failed",
        "error": f"{tool.name} failed: {error}",
    }


def sanitize_tool_response(response: dict, tool_name: str = "") -> dict:
    safe = dict(response)
    preserve_metadata = tool_name in {
        "computer_see",
        "computer_inspect_ui",
        "computer_surfaces",
        "computer_window",
        "computer_app",
    }
    content = safe.get("content")
    if isinstance(content, list):
        text_blocks = []
        omitted_images = 0
        for block in content:
            if not isinstance(block, dict):
                continue
            if (
                block.get("type") == "text"
                and isinstance(block.get("text"), str)
            ):
                text_blocks.append({"type": "text", "text": block["text"]})
            elif block.get("type") in {"image", "audio"}:
                omitted_images += 1
        safe["content"] = text_blocks
        if omitted_images:
            safe["media_omitted"] = omitted_images
    metadata = safe.pop("_meta", None) or safe.pop("meta", None)
    if isinstance(metadata, dict):
        if preserve_metadata:
            safe["metadata"] = metadata
        elif tool_name.startswith("computer_"):
            receipt_keys = {
                "dispatch_state",
                "effect",
                "escalation",
                "evidence",
                "mutation_dispatched",
                "requires_fresh_observation",
                "retry_safe",
                "retry_safety",
                "route",
                "state",
                "target_identity",
                "target_receipt",
            }
            receipt = {
                key: value
                for key, value in metadata.items()
                if key in receipt_keys
            }
            if receipt:
                safe["metadata"] = receipt
    return safe


def normalize_tool_outcome(
    tool_name: str,
    args: dict[str, Any],
    response: dict,
) -> dict:
    """Convert known transport signals into truthful domain outcomes."""
    if not tool_name.startswith("browser_"):
        return response
    message = response_error(response)
    if "download is starting" not in message.casefold():
        return response
    return {
        "status": "download_started",
        "outcome": "Chrome accepted the download request. The saved file has not yet been verified on disk.",
        "source_url": str(args.get("url", "")),
        "verification_required": True,
    }


def tool_call_key(tool: BaseTool, tool_context: ToolContext) -> str:
    return tool_context.function_call_id or f"{tool_context.session.id}:{tool.name}"


def tool_duration_ms(tool: BaseTool, tool_context: ToolContext) -> int:
    started_at = tool_started_at.pop(tool_call_key(tool, tool_context), None)
    return round((time.perf_counter() - started_at) * 1000) if started_at else 0


def tool_target(args: dict[str, Any]) -> str:
    safe_keys = ("app", "action", "element", "url", "range", "query", "spreadsheet_id")
    values = [f"{key}={str(args[key])[:120]}" for key in safe_keys if args.get(key)]
    return " ".join(values) or "-"


def normalize_tool_args(tool_name: str, args: dict[str, Any]) -> str | None:
    if tool_name == "computer_app" and str(args.get("action", "")).lower() == "open":
        return "computer_app does not support action=open. Use action=launch for an installed application."
    if tool_name == "computer_dialog":
        action = str(args.get("action", "")).casefold()
        if not action:
            return "computer_dialog requires an explicit action."
        has_app = isinstance(args.get("app"), str) and bool(args["app"].strip())
        has_pid = isinstance(args.get("pid"), int) and not isinstance(args.get("pid"), bool)
        has_window = isinstance(args.get("window_id"), int) and not isinstance(args.get("window_id"), bool)
        if not (has_app or has_pid or has_window):
            return "computer_dialog requires an originating app, PID, or exact window ID."
        if action == "file":
            path = args.get("path")
            if not isinstance(path, str) or not path.strip():
                return "computer_dialog action=file requires the exact absolute file path."
            file_path = Path(path).expanduser()
            if not file_path.is_absolute():
                return "computer_dialog action=file requires an absolute file path."
            if not file_path.is_file():
                return f"The selected local file does not exist: {file_path}"
            args["path"] = str(file_path)
    app_target = args.get("app")
    if isinstance(app_target, str):
        pid_target = COMPOUND_PID_TARGET.fullmatch(app_target.strip())
        if pid_target:
            args.pop("app")
            args["pid"] = int(pid_target.group(1))
            window_title = (pid_target.group(2) or "").strip()
            if window_title:
                args.setdefault("window_title", window_title)
    if tool_name.startswith("browser_"):
        target = args.get("target")
        if isinstance(target, str):
            clean = target.strip()
            if clean.startswith("ref="):
                clean = clean.removeprefix("ref=").strip()
            if not clean:
                return "The browser target is empty. Observe the page again and use a fresh reference."
            args["target"] = clean
    if tool_name == "browser_evaluate":
        if args.get("filename"):
            return "Browser code must be supplied inline; loading code from files is disabled."
        code = args.get("function")
        if not isinstance(code, str) or not code.strip():
            return "Browser code is empty."
        if BROWSER_EVALUATE_FORBIDDEN.search(code):
            return (
                "Browser code may only transform the current page DOM. Network, storage, "
                "credential, navigation, dynamic-code, and form-submission APIs are disabled."
            )
    separate_window_title_tools = {
        "computer_dialog",
        "computer_press",
        "computer_type",
    }
    if tool_name in separate_window_title_tools:
        value = args.get("app")
        if isinstance(value, str) and ":" in value:
            app_name, window_title = value.split(":", 1)
            if app_name.strip() and window_title.strip():
                args["app"] = app_name.strip()
                args.setdefault("window_title", window_title.strip())
    return None


def response_error(response: dict) -> str:
    error = response.get("error")
    if isinstance(error, str):
        return error[:1000]
    content = response.get("content")
    if isinstance(content, list):
        return " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )[:1000]
    return "Unknown tool error"


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
