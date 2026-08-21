from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.genai import types


MANIFEST_PATH = Path(__file__).with_name("tool_manifest.json")
REMOTE_TOOL_URL = os.getenv("SHERPA_REMOTE_TOOL_URL", "").rstrip("/")
REMOTE_TOOL_SECRET = os.getenv("SHERPA_INTERNAL_SECRET", "")
INSTALLATION_ID = os.getenv("SHERPA_INSTALLATION_ID", "default")
_client: httpx.AsyncClient | None = None


def remote_tools_enabled() -> bool:
    return bool(REMOTE_TOOL_URL)


def tool_manifest() -> dict[str, list[dict[str, Any]]]:
    return json.loads(MANIFEST_PATH.read_text())


async def http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(900, connect=10))
    return _client


class RemoteTool(BaseTool):
    """Preserve a local tool declaration while executing it through Sherpa's relay."""

    def __init__(self, declaration: dict[str, Any]) -> None:
        parsed = types.FunctionDeclaration.model_validate(declaration)
        super().__init__(name=parsed.name, description=parsed.description or "")
        self.declaration = parsed

    def _get_declaration(self) -> types.FunctionDeclaration:
        return self.declaration

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Any:
        if not REMOTE_TOOL_SECRET:
            raise RuntimeError("Sherpa remote tool authentication is not configured")
        response = await (await http_client()).post(
            f"{REMOTE_TOOL_URL}/agent/tools/{self.name}",
            headers={"X-Sherpa-Agent-Secret": REMOTE_TOOL_SECRET},
            json={
                "installation_id": INSTALLATION_ID,
                "function_call_id": tool_context.function_call_id,
                "args": args,
                "state": tool_context.state.to_dict(),
            },
        )
        if response.is_error:
            detail = (
                response.json().get("detail", response.text)
                if response.headers.get("content-type", "").startswith("application/json")
                else response.text
            )
            raise RuntimeError(
                f"Sherpa tool relay returned {response.status_code}: {detail}"
            )
        return response.json()


class RemoteToolset(BaseToolset):
    def __init__(self, namespace: str) -> None:
        super().__init__()
        self.permission_id = namespace
        self._tools = [RemoteTool(item) for item in tool_manifest().get(namespace, [])]

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        del readonly_context
        return self._tools


def remote_toolset(namespace: str) -> RemoteToolset:
    return RemoteToolset(namespace)


def remote_local_tools() -> list[RemoteTool]:
    return [RemoteTool(item) for item in tool_manifest().get("local", [])]
