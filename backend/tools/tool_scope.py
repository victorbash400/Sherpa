import asyncio
from collections.abc import AsyncIterator, Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset


_active_capabilities: ContextVar[frozenset[str] | None] = ContextVar(
    "sherpa_tool_capabilities",
    default=None,
)


def capability_enabled(capability: str) -> bool:
    active = _active_capabilities.get()
    return active is None or capability in active


@contextmanager
def tool_scope(capabilities: Iterable[str]):
    token = _active_capabilities.set(frozenset(capabilities))
    try:
        yield
    finally:
        _active_capabilities.reset(token)


async def run_with_tool_scope(
    runner: Any,
    capabilities: Iterable[str],
    **run_arguments: Any,
) -> AsyncIterator[Any]:
    with tool_scope(capabilities):
        async for event in runner.run_async(**run_arguments):
            yield event


class ScopedToolset(BaseToolset):
    def __init__(self, delegate: BaseToolset, capability: str) -> None:
        super().__init__()
        self.delegate = delegate
        self.capability = capability
        self._catalog_lock = asyncio.Lock()

    async def get_tools(
        self,
        readonly_context: ReadonlyContext | None = None,
    ) -> list[BaseTool]:
        if not capability_enabled(self.capability):
            return []
        async with self._catalog_lock:
            return await self.delegate.get_tools_with_prefix(readonly_context)

    async def close(self) -> None:
        await self.delegate.close()
