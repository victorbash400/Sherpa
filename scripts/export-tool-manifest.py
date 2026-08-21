import asyncio
import json
from pathlib import Path

from google.adk.tools import FunctionTool

from backend.tool_registry import browser_tools, cloud_tools, computer_tools, workspace_tools
from backend.tools.local_artifacts import inspect_local_artifacts
from backend.tools.memory import save_memory


OUTPUT = Path(__file__).resolve().parents[1] / "backend" / "tool_manifest.json"


async def declarations() -> dict[str, list[dict[str, object]]]:
    manifest: dict[str, list[dict[str, object]]] = {
        "local": [],
        "computer": [],
        "browser": [],
    }
    manifest["local"] = [
        tool._get_declaration().model_dump(mode="json", exclude_none=True)
        for tool in (FunctionTool(inspect_local_artifacts), FunctionTool(save_memory))
    ]
    for namespace, toolset in (("computer", computer_tools), ("browser", browser_tools)):
        manifest[namespace] = [
            tool._get_declaration().model_dump(mode="json", exclude_none=True)
            for tool in await toolset.get_tools_with_prefix()
        ]
    for toolset in workspace_tools:
        manifest[toolset.permission_id] = [
            tool._get_declaration().model_dump(mode="json", exclude_none=True)
            for tool in toolset._tools
        ]
    for toolset in cloud_tools:
        try:
            tools = await toolset.get_tools_with_prefix()
        except RuntimeError as error:
            print(f"Skipping unavailable {toolset.permission_id}: {error}")
            tools = []
        manifest[toolset.permission_id] = [
            tool._get_declaration().model_dump(mode="json", exclude_none=True)
            for tool in tools
        ]
    return manifest


async def main() -> None:
    manifest = await declarations()
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {sum(map(len, manifest.values()))} tools to {OUTPUT}")
    await browser_tools.close()
    await computer_tools.close()
    await asyncio.gather(*(toolset.close() for toolset in cloud_tools))


asyncio.run(main())
