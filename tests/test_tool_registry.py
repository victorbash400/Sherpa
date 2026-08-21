import unittest

from backend.agents.sherpa_agent import create_sherpa_agent
from backend.tool_registry import (
    LOADED_TOOLS_STATE,
    capability_catalog,
    tool_registry,
)


class FakeToolContext:
    def __init__(self) -> None:
        self.state: dict[str, object] = {}


class ToolRegistryTests(unittest.IsolatedAsyncioTestCase):
    def test_every_worker_starts_with_dynamic_registry(self) -> None:
        unskilled = create_sherpa_agent([])
        whatsapp = create_sherpa_agent(["native-whatsapp"])

        self.assertEqual(len(unskilled.tools), 6)
        self.assertEqual(len(whatsapp.tools), 6)
        self.assertIs(unskilled.tools[-1], tool_registry)
        self.assertIs(whatsapp.tools[-1], tool_registry)

    def test_catalog_exposes_every_namespace_compactly(self) -> None:
        catalog = capability_catalog()

        self.assertIn(
            {
                "id": "computer",
                "description": "Operate macOS applications, windows, dialogs, menus, and controls.",
            },
            catalog,
        )
        self.assertIn(
            {
                "id": "workspace.gmail",
                "description": "Search, read, draft, send, and organize Gmail.",
            },
            catalog,
        )

    async def test_namespace_list_returns_exact_ids_without_a_query(self) -> None:
        result = await tool_registry.list_tool_namespaces()

        match_ids = [match["id"] for match in result["namespaces"]]
        self.assertIn("computer", match_ids)
        self.assertIn("workspace.gmail", match_ids)
        self.assertIn("workspace.drive", match_ids)

    async def test_worker_can_load_additional_namespaces_during_task(self) -> None:
        context = FakeToolContext()

        first = await tool_registry.load_tools(
            ["computer"],
            context,  # type: ignore[arg-type]
        )
        second = await tool_registry.load_tools(
            ["workspace.gmail"],
            context,  # type: ignore[arg-type]
        )

        self.assertEqual(first["status"], "loaded")
        self.assertEqual(second["status"], "loaded")
        self.assertEqual(
            context.state[LOADED_TOOLS_STATE],
            [
                "computer",
                "workspace.gmail",
            ],
        )

    async def test_unknown_namespace_is_explicitly_rejected(self) -> None:
        context = FakeToolContext()

        result = await tool_registry.load_tools(
            ["workspace.unknown"],
            context,  # type: ignore[arg-type]
        )

        self.assertEqual(result["status"], "not_found")
        self.assertEqual(context.state, {})


if __name__ == "__main__":
    unittest.main()
