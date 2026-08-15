import asyncio
import unittest

from backend.tools.tool_scope import capability_enabled, tool_scope


class ToolScopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_agents_keep_independent_capabilities(self) -> None:
        ready = asyncio.Event()
        observed: dict[str, tuple[bool, bool]] = {}

        async def inspect(name: str, capability: str) -> None:
            with tool_scope([capability]):
                if name == "computer":
                    ready.set()
                else:
                    await ready.wait()
                await asyncio.sleep(0)
                observed[name] = (
                    capability_enabled("computer"),
                    capability_enabled("workspace.gmail"),
                )

        await asyncio.gather(
            inspect("computer", "computer"),
            inspect("mail", "workspace.gmail"),
        )

        self.assertEqual(observed["computer"], (True, False))
        self.assertEqual(observed["mail"], (False, True))


if __name__ == "__main__":
    unittest.main()
