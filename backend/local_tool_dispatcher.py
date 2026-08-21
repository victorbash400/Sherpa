from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.base_tool import BaseTool

from backend.remote_tools import tool_manifest
from backend.tool_registry import browser_tools, cloud_tools, computer_tools, workspace_tools
from backend.tools.computer_use.callbacks import (
    after_computer_tool,
    before_computer_tool,
    on_computer_tool_error,
)
from backend.tools.local_artifacts import inspect_local_artifacts
from backend.tools.memory import save_memory
from backend.account_context import account_context


class RelayState(dict[str, Any]):
    def to_dict(self) -> dict[str, Any]:
        return dict(self)


class RelayToolContext:
    def __init__(
        self,
        state: dict[str, Any],
        function_call_id: str,
        session_id: str,
    ) -> None:
        self.state = RelayState(state)
        self.function_call_id = function_call_id
        self.session = SimpleNamespace(id=session_id)
        self.tool_confirmation = None
        self.custom_metadata: dict[str, Any] = {}

    def request_confirmation(self, **_: Any) -> None:
        raise RuntimeError("Local tool confirmation must be handled before relay dispatch")


@dataclass
class LocalToolDispatcher:
    _tools: dict[str, BaseTool] | None = None
    _lock: asyncio.Lock | None = None

    def __post_init__(self) -> None:
        self._tools = {
            "inspect_local_artifacts": FunctionTool(inspect_local_artifacts),
            "save_memory": FunctionTool(save_memory),
        }
        self._namespace_by_tool = {
            declaration["name"]: namespace
            for namespace, declarations in tool_manifest().items()
            for declaration in declarations
        }
        self._loaded_namespaces = {"local"}

    async def load_namespace(self, namespace: str) -> None:
        if namespace in self._loaded_namespaces:
            return
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if namespace in self._loaded_namespaces:
                return
            if namespace == "computer":
                toolsets = [computer_tools]
            elif namespace == "browser":
                toolsets = [browser_tools]
            elif namespace.startswith("workspace."):
                toolsets = [
                    toolset
                    for toolset in workspace_tools
                    if toolset.permission_id == namespace
                ]
            elif namespace.startswith("cloud."):
                toolsets = [
                    toolset for toolset in cloud_tools if toolset.permission_id == namespace
                ]
            else:
                toolsets = []
            for toolset in toolsets:
                try:
                    for tool in await toolset.get_tools_with_prefix():
                        self._tools[tool.name] = tool  # type: ignore[index]
                except RuntimeError:
                    continue
            self._loaded_namespaces.add(namespace)

    async def tool(self, name: str) -> BaseTool | None:
        namespace = self._namespace_by_tool.get(name)
        if namespace:
            await self.load_namespace(namespace)
        return self._tools.get(name)  # type: ignore[union-attr]

    async def run(
        self,
        *,
        name: str,
        args: dict[str, Any],
        state: dict[str, Any],
        function_call_id: str,
        session_id: str,
    ) -> Any:
        account = account_context.current()
        request_account_id = str(state.get("account_id") or "")
        if not account or request_account_id != account.id:
            return {
                "status": "failed",
                "error": "This tool request does not belong to the signed-in Sherpa account.",
            }
        tool = await self.tool(name)
        if not tool:
            return {"status": "failed", "error": f"Local tool is unavailable: {name}"}
        context = RelayToolContext(state, function_call_id, session_id)
        if name.startswith("computer_") or name.startswith("browser_"):
            rejected = await before_computer_tool(tool, args, context)  # type: ignore[arg-type]
            if rejected:
                return rejected
        try:
            result = await tool.run_async(args=args, tool_context=context)  # type: ignore[arg-type]
        except Exception as error:
            if name.startswith("computer_") or name.startswith("browser_"):
                return await on_computer_tool_error(  # type: ignore[arg-type]
                    tool,
                    args,
                    context,
                    error,
                )
            return {"status": "failed", "error": f"{name} failed: {error}"}
        if name.startswith("computer_") or name.startswith("browser_"):
            return await after_computer_tool(  # type: ignore[arg-type]
                tool,
                args,
                context,
                result,
            )
        return result


local_tool_dispatcher = LocalToolDispatcher()
