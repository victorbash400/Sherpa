import asyncio
import json
from pathlib import Path
from typing import Any

from backend.permission_store import permission_store


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PEEKABOO_BINARY = PROJECT_ROOT / "node_modules" / ".bin" / "peekaboo"


async def connection_snapshot() -> dict[str, Any]:
    apps_result = await peekaboo_json("app", "list")
    apps = apps_result.get("data", {}).get("apps", [])
    permission_store.register_apps(apps)

    return {
        "sections": [
            {
                "id": "google",
                "title": "Google",
                "permissions": [
                    permission(
                        "google.models",
                        "Gemini models",
                        "Allow Sherpa to use Gemini 3.7 Flash and Gemini 3.1 Flash Live",
                    )
                ],
            },
            {
                "id": "browser",
                "title": "Browser",
                "permissions": [
                    permission("browser.read", "Read pages", "Read page structure and visible content"),
                    permission("browser.interact", "Interact with pages", "Navigate, click, type, select, and upload"),
                    permission("browser.tabs", "Manage tabs", "Open, switch, and close Chrome tabs"),
                ],
            },
            {
                "id": "computer",
                "title": "Mac",
                "permissions": [
                    permission("mac.screen", "See your screen", "Read application windows and interface controls"),
                    permission("mac.control", "Control applications", "Click, type, scroll, and use application menus"),
                ],
            },
            {
                "id": "apps",
                "title": "Applications",
                "permissions": [
                    permission(
                        f"app.{app['bundle_id']}",
                        app["name"],
                        "Allow Sherpa to interact with this application",
                    )
                    for app in apps
                    if app.get("name") and app.get("bundle_id")
                ],
            },
        ]
    }


def permission(permission_id: str, name: str, description: str) -> dict[str, Any]:
    return {
        "id": permission_id,
        "name": name,
        "description": description,
        "enabled": permission_store.enabled(permission_id),
    }


async def peekaboo_json(*arguments: str) -> dict[str, Any]:
    if not PEEKABOO_BINARY.is_file():
        return {}
    process = await asyncio.create_subprocess_exec(
        str(PEEKABOO_BINARY),
        *arguments,
        "--json-output",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await process.communicate()
    if process.returncode != 0:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {}
