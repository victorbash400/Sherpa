import re
from dataclasses import dataclass

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionTool, ToolContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset

from backend.tools.browser_use import create_playwright_toolset
from backend.tools.computer_use import create_peekaboo_toolset
from backend.tools.google_tools import create_google_cloud_toolsets, create_workspace_toolsets


LOADED_TOOLS_STATE = "loaded_tool_ids"


@dataclass(frozen=True)
class ToolCapability:
    id: str
    description: str
    terms: tuple[str, ...]


CAPABILITIES = (
    ToolCapability(
        "browser",
        "Navigate and operate the connected Chrome browser.",
        ("browser", "chrome", "website", "web", "page", "tab"),
    ),
    ToolCapability(
        "workspace.gmail",
        "Search, read, draft, send, and organize Gmail.",
        ("gmail", "email", "mail", "inbox", "message"),
    ),
    ToolCapability(
        "workspace.drive",
        "Find, read, upload, download, share, and organize Google Drive files.",
        ("drive", "file", "folder", "upload", "download", "share"),
    ),
    ToolCapability(
        "workspace.docs",
        "Create, read, and edit Google Docs.",
        ("doc", "docs", "document", "writing"),
    ),
    ToolCapability(
        "workspace.sheets",
        "Create, read, update, and format Google Sheets.",
        ("sheet", "sheets", "spreadsheet", "cells", "table"),
    ),
    ToolCapability(
        "workspace.slides",
        "Create, read, and edit Google Slides.",
        ("slide", "slides", "presentation", "deck"),
    ),
    ToolCapability(
        "workspace.calendar",
        "Inspect and manage Google Calendar events and availability.",
        ("calendar", "event", "availability", "schedule", "meeting"),
    ),
    ToolCapability(
        "workspace.people",
        "Resolve people through Google Contacts.",
        ("people", "person", "contact", "contacts", "recipient"),
    ),
    ToolCapability(
        "workspace.tasks",
        "Inspect and manage Google Tasks.",
        ("task", "tasks", "todo", "reminder"),
    ),
    ToolCapability(
        "workspace.forms",
        "Create, edit, publish, and read Google Forms.",
        ("form", "forms", "survey", "quiz", "responses"),
    ),
    ToolCapability(
        "workspace.meet",
        "Create and inspect Google Meet spaces and artifacts.",
        ("meet", "video call", "recording", "transcript"),
    ),
    ToolCapability(
        "cloud.resources",
        "Inspect and manage Google Cloud project resources.",
        ("gcp", "google cloud", "cloud", "project", "resource"),
    ),
    ToolCapability(
        "cloud.cli",
        "Run supported Google Cloud operations.",
        ("gcloud", "cloud cli", "command", "operation"),
    ),
)

COMPUTER_CAPABILITIES = (
    ToolCapability("computer.app", "List, launch, focus, hide, or quit macOS applications.", ("app", "application", "launch", "open", "focus")),
    ToolCapability("computer.inspect_ui", "Inspect controls and text in a specific application window.", ("inspect", "observe", "find", "control", "accessibility", "ui")),
    ToolCapability("computer.surfaces", "List applications, windows, dialogs, and sheets to select an exact target.", ("surface", "window", "dialog", "sheet", "target", "list")),
    ToolCapability("computer.window", "List, focus, move, resize, minimize, maximize, or close windows.", ("window", "focus", "move", "resize", "minimize", "maximize", "close")),
    ToolCapability("computer.dialog", "Select a file or submit text through a native macOS dialog.", ("dialog", "file", "attach", "upload", "picker", "open panel", "save panel")),
    ToolCapability("computer.click", "Click an inspected macOS interface element.", ("click", "select", "press", "button", "control")),
    ToolCapability("computer.type", "Type or replace text in a macOS interface element.", ("type", "text", "enter", "fill", "replace")),
    ToolCapability("computer.press", "Press a keyboard key or shortcut in a macOS application.", ("key", "keyboard", "shortcut", "press", "enter", "escape")),
    ToolCapability("computer.scroll", "Scroll within a macOS window or control.", ("scroll", "up", "down", "left", "right")),
    ToolCapability("computer.menu", "Inspect or select a macOS application menu item.", ("menu", "menu item", "command")),
    ToolCapability("computer.drag", "Drag between coordinates or inspected macOS elements.", ("drag", "drop", "move")),
    ToolCapability("computer.set_value", "Set the value of a supported macOS accessibility control.", ("set", "value", "slider", "field")),
    ToolCapability("computer.action", "Run an advertised accessibility action on an inspected element.", ("accessibility", "action", "element")),
    ToolCapability("computer.permissions", "Inspect macOS permissions required for computer control.", ("permission", "accessibility", "screen recording")),
)

SEARCHABLE_CAPABILITIES = (*COMPUTER_CAPABILITIES, *CAPABILITIES)

computer_tools = create_peekaboo_toolset()
browser_tools = create_playwright_toolset()
workspace_tools = create_workspace_toolsets()
cloud_tools = create_google_cloud_toolsets()


def capability_catalog() -> list[dict[str, str]]:
    return [{"id": item.id, "description": item.description} for item in SEARCHABLE_CAPABILITIES]


def _terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


class DynamicToolRegistry(BaseToolset):
    """Expose compact discovery first, then session-selected tool namespaces."""

    def __init__(self) -> None:
        super().__init__()
        self._use_invocation_cache = False
        self._search_tool = FunctionTool(self.search_tools)
        self._load_tool = FunctionTool(self.load_tools)
        self._toolsets = {
            "browser": browser_tools,
            **{toolset.permission_id: toolset for toolset in workspace_tools},
            **{toolset.permission_id: toolset for toolset in cloud_tools},
        }

    async def search_tools(self, query: str) -> dict[str, object]:
        """Search the compact tool registry for capabilities matching an intended action."""
        query_terms = _terms(query)
        ranked: list[tuple[int, int, ToolCapability]] = []
        for index, capability in enumerate(SEARCHABLE_CAPABILITIES):
            searchable = _terms(
                " ".join((capability.id, capability.description, *capability.terms))
            )
            score = len(query_terms & searchable)
            if score:
                ranked.append((score, index, capability))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        matches = [item for _, _, item in ranked[:8]]
        if not matches:
            matches = list(SEARCHABLE_CAPABILITIES)
        return {
            "matches": [
                {"id": item.id, "description": item.description}
                for item in matches
            ],
            "next": "Call load_tools once with the IDs needed for the task.",
        }

    async def load_tools(
        self,
        tool_ids: list[str],
        tool_context: ToolContext,
    ) -> dict[str, object]:
        """Load exact tool or namespace IDs returned by search_tools into this session."""
        known_ids = {
            *(item.id for item in COMPUTER_CAPABILITIES),
            *self._toolsets,
        }
        unknown = [tool_id for tool_id in tool_ids if tool_id not in known_ids]
        if unknown:
            return {
                "status": "not_found",
                "unknown_ids": unknown,
                "guidance": "Call search_tools and use only exact returned IDs.",
            }
        loaded = list(tool_context.state.get(LOADED_TOOLS_STATE, []))
        for tool_id in tool_ids:
            if tool_id not in loaded:
                loaded.append(tool_id)
        tool_context.state[LOADED_TOOLS_STATE] = loaded
        return {
            "status": "loaded",
            "loaded_tool_ids": loaded,
            "next": "The selected tools are available on the next model step.",
        }

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        tools: list[BaseTool] = [self._search_tool, self._load_tool]
        loaded = (
            readonly_context.state.get(LOADED_TOOLS_STATE, [])
            if readonly_context
            else []
        )
        computer_names = {
            tool_id.replace("computer.", "computer_", 1)
            for tool_id in loaded
            if tool_id.startswith("computer.")
        }
        if computer_names:
            computer_catalog = await computer_tools.get_tools_with_prefix(readonly_context)
            tools.extend(tool for tool in computer_catalog if tool.name in computer_names)
        for tool_id in loaded:
            toolset = self._toolsets.get(tool_id)
            if toolset:
                tools.extend(await toolset.get_tools_with_prefix(readonly_context))
        return tools


tool_registry = DynamicToolRegistry()
