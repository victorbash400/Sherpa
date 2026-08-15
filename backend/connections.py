import os
import plistlib
import unicodedata
from pathlib import Path
from typing import Any
from xml.parsers.expat import ExpatError

from backend.permission_store import permission_store
from backend.google_auth import google_auth


async def connection_snapshot() -> dict[str, Any]:
    apps = installed_applications()
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
                "id": "workspace",
                "title": "Google Workspace",
                "permissions": [
                    google_connection("workspace", "Google Workspace account"),
                    permission("workspace.drive", "Google Drive", "Search, read, create, and organize Drive files"),
                    permission("workspace.docs", "Google Docs", "Read and update Google documents"),
                    permission("workspace.sheets", "Google Sheets", "Read and update spreadsheets"),
                    permission("workspace.slides", "Google Slides", "Read and update presentations"),
                    permission("workspace.gmail", "Gmail", "Read mail and create drafts"),
                    permission("workspace.calendar", "Google Calendar", "Read and manage calendar events"),
                    permission("workspace.people", "Google Contacts", "Find people and contact details"),
                ],
            },
            {
                "id": "cloud",
                "title": "Google Cloud",
                "permissions": [
                    google_connection("cloud", "Google Cloud account"),
                    permission("cloud.resources", "Cloud resources", "Inspect and manage projects and resources through Google MCP"),
                    permission("cloud.cli", "Cloud operations", "Run supported Google Cloud operations through Google MCP"),
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


def installed_applications() -> list[dict[str, str]]:
    """Return installed macOS application bundles, not merely running apps."""
    applications: dict[str, dict[str, str]] = {}
    roots = (
        Path("/Applications"),
        Path("/System/Applications"),
        Path.home() / "Applications",
    )
    for root in roots:
        if not root.is_dir():
            continue
        for directory, child_directories, _ in os.walk(root):
            bundle_path = Path(directory)
            if bundle_path.suffix != ".app":
                continue
            child_directories.clear()
            app = application_metadata(bundle_path)
            if app:
                applications.setdefault(app["bundle_id"], app)
    return sorted(
        applications.values(),
        key=lambda app: app["name"].casefold(),
    )


def application_metadata(bundle_path: Path) -> dict[str, str] | None:
    plist_path = bundle_path / "Contents" / "Info.plist"
    try:
        with plist_path.open("rb") as plist_file:
            metadata = plistlib.load(plist_file)
    except (FileNotFoundError, OSError, plistlib.InvalidFileException, ExpatError):
        return None
    bundle_id = metadata.get("CFBundleIdentifier")
    name = (
        metadata.get("CFBundleDisplayName")
        or metadata.get("CFBundleName")
        or bundle_path.stem
    )
    if not isinstance(bundle_id, str) or not bundle_id.strip():
        return None
    if not isinstance(name, str) or not name.strip():
        return None
    clean_name = "".join(
        character for character in name
        if unicodedata.category(character) != "Cf"
    ).strip()
    if not clean_name:
        return None
    return {
        "bundle_id": bundle_id.strip(),
        "name": clean_name,
    }


def permission(permission_id: str, name: str, description: str) -> dict[str, Any]:
    return {
        "id": permission_id,
        "name": name,
        "description": description,
        "enabled": permission_store.enabled(permission_id),
    }


def google_connection(connection_id: str, name: str) -> dict[str, Any]:
    state = google_auth.snapshot(connection_id)  # type: ignore[arg-type]
    email = state.get("email")
    return {
        "id": f"connection.google_{connection_id}",
        "name": name,
        "description": email or "Allow Sherpa to use your Google account",
        "enabled": state["connected"],
        "connection": f"google_{connection_id}",
        "configured": state["configured"],
        "profile": {
            "email": email,
            "name": state.get("name"),
            "picture": (
                "http://127.0.0.1:8000/oauth/google/workspace/avatar"
                if connection_id == "workspace" and state.get("picture")
                else None
            ),
        },
    }
