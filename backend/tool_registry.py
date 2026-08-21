import logging
import time
from dataclasses import dataclass

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import FunctionTool, ToolContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset

from backend.tools.browser_use import create_playwright_toolset
from backend.tools.computer_use import create_peekaboo_toolset
from backend.tools.google_tools import create_google_cloud_toolsets, create_workspace_toolsets
from backend.remote_tools import remote_tools_enabled, remote_toolset


LOADED_TOOLS_STATE = "loaded_tool_ids"
logger = logging.getLogger("sherpa.tool_registry")


@dataclass(frozen=True)
class ToolCapability:
    id: str
    description: str
    terms: tuple[str, ...]


CAPABILITIES = (
    ToolCapability(
        "computer",
        "Operate macOS applications, windows, dialogs, menus, and controls.",
        ("macos", "application", "window", "dialog", "menu", "computer"),
    ),
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

SEARCHABLE_CAPABILITIES = CAPABILITIES

SKILL_NAMESPACES = {
    "chrome-web-workflows": ("browser",),
    "google-cloud-operations": ("cloud.resources", "cloud.cli"),
    "native-macos-apps": ("computer",),
    "native-whatsapp": ("computer",),
    "workspace-documents": ("workspace.drive", "workspace.docs"),
    "workspace-email": ("workspace.gmail", "workspace.drive"),
    "workspace-forms": ("workspace.forms", "workspace.drive"),
    "workspace-meet": ("workspace.meet", "workspace.drive"),
    "workspace-presentations": ("workspace.slides", "workspace.drive"),
    "workspace-scheduling": ("workspace.calendar", "workspace.people"),
    "workspace-spreadsheets": ("workspace.sheets", "workspace.drive"),
    "workspace-tasks": ("workspace.tasks",),
}

if remote_tools_enabled():
    computer_tools = remote_toolset("computer")
    browser_tools = remote_toolset("browser")
    workspace_tools = [
        remote_toolset(capability.id)
        for capability in CAPABILITIES
        if capability.id.startswith("workspace.")
    ]
    cloud_tools = [remote_toolset("cloud.resources"), remote_toolset("cloud.cli")]
else:
    computer_tools = create_peekaboo_toolset()
    browser_tools = create_playwright_toolset()
    workspace_tools = create_workspace_toolsets()
    cloud_tools = create_google_cloud_toolsets()


def capability_catalog() -> list[dict[str, str]]:
    return [{"id": item.id, "description": item.description} for item in SEARCHABLE_CAPABILITIES]


def capability_catalog_prompt() -> str:
    return "\n".join(
        f"- `{item.id}`: {item.description}"
        for item in SEARCHABLE_CAPABILITIES
    )


def namespaces_for_skills(skill_ids: list[str] | None) -> list[str]:
    namespaces: list[str] = []
    for skill_id in skill_ids or []:
        for namespace in SKILL_NAMESPACES.get(skill_id, ()):
            if namespace not in namespaces:
                namespaces.append(namespace)
    return namespaces


class DynamicToolRegistry(BaseToolset):
    """Load additional tool namespaces that were not preloaded for this task."""

    def __init__(self, initial_namespace_ids: list[str] | None = None) -> None:
        super().__init__()
        self._use_invocation_cache = False
        self._load_tool = FunctionTool(self.load_tools)
        self._initial_namespace_ids = tuple(initial_namespace_ids or ())
        self._toolsets = {
            "computer": computer_tools,
            "browser": browser_tools,
            **{toolset.permission_id: toolset for toolset in workspace_tools},
            **{toolset.permission_id: toolset for toolset in cloud_tools},
        }

    async def load_tools(
        self,
        tool_ids: list[str],
        tool_context: ToolContext,
    ) -> dict[str, object]:
        """Load exact namespace IDs from the namespace directory in your instructions."""
        known_ids = set(self._toolsets)
        unknown = [tool_id for tool_id in tool_ids if tool_id not in known_ids]
        if unknown:
            return {
                "status": "not_found",
                "unknown_ids": unknown,
                "guidance": "Use only exact IDs from the namespace directory in your instructions.",
            }
        loaded = list(tool_context.state.get(LOADED_TOOLS_STATE, []))
        for tool_id in tool_ids:
            if tool_id not in self._initial_namespace_ids and tool_id not in loaded:
                loaded.append(tool_id)
        tool_context.state[LOADED_TOOLS_STATE] = loaded
        return {
            "status": "loaded",
            "loaded_tool_ids": [*self._initial_namespace_ids, *loaded],
            "next": "The selected tools are available on the next model step.",
        }

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        started_at = time.perf_counter()
        tools: list[BaseTool] = [self._load_tool]
        loaded = (
            readonly_context.state.get(LOADED_TOOLS_STATE, [])
            if readonly_context
            else []
        )
        for tool_id in loaded:
            toolset = self._toolsets.get(tool_id)
            if toolset:
                namespace_started_at = time.perf_counter()
                namespace_tools = await toolset.get_tools_with_prefix(readonly_context)
                tools.extend(namespace_tools)
                logger.info(
                    "namespace.ready id=%s duration_ms=%d tools=%d names=%s",
                    tool_id,
                    round((time.perf_counter() - namespace_started_at) * 1000),
                    len(namespace_tools),
                    ",".join(tool.name for tool in namespace_tools),
                )
        logger.info(
            "catalog.ready loaded=%s duration_ms=%d tools=%d",
            ",".join(loaded) or "none",
            round((time.perf_counter() - started_at) * 1000),
            len(tools),
        )
        return tools

    def initial_toolsets(self) -> list[BaseToolset]:
        return [
            self._toolsets[namespace]
            for namespace in self._initial_namespace_ids
            if namespace in self._toolsets
        ]


tool_registry = DynamicToolRegistry()
