import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any


PERMISSION_FILE = Path.home() / "Library" / "Application Support" / "Sherpa" / "permissions.json"
PID_TARGET = re.compile(r"pid\s*:\s*(\d+)", re.IGNORECASE)
DEFAULT_PERMISSIONS = {
    "google.models": True,
    "browser.read": True,
    "browser.interact": True,
    "browser.tabs": True,
    "mac.screen": True,
    "mac.control": True,
    "workspace.drive": True,
    "workspace.docs": True,
    "workspace.sheets": True,
    "workspace.slides": True,
    "workspace.gmail": True,
    "workspace.calendar": True,
    "workspace.people": True,
    "cloud.resources": True,
    "cloud.cli": True,
}


class PermissionStore:
    def __init__(self) -> None:
        self._values = self._load()
        self._app_aliases: dict[str, str] = {}

    def enabled(self, permission_id: str) -> bool:
        return self._values.get(permission_id, True)

    def set(self, permission_id: str, enabled: bool) -> None:
        self._values[permission_id] = enabled
        PERMISSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        PERMISSION_FILE.write_text(json.dumps(self._values, indent=2) + "\n")

    def register_apps(self, apps: list[dict[str, Any]]) -> None:
        for app in apps:
            bundle_id = app.get("bundle_id")
            if isinstance(bundle_id, str) and bundle_id:
                self._values.setdefault(f"app.{bundle_id}", True)
                name = app.get("name")
                if isinstance(name, str):
                    self._app_aliases[normalize_app_name(name)] = bundle_id

    def app_enabled(self, target: str) -> bool:
        normalized = normalize_app_name(target)
        pid_match = PID_TARGET.fullmatch(normalized)
        if pid_match:
            bundle_id = bundle_id_for_pid(int(pid_match.group(1)))
            if not bundle_id:
                return False
            normalized = normalize_app_name(bundle_id)
        normalized = normalize_app_name(self._app_aliases.get(normalized, normalized))
        for permission_id, enabled in self._values.items():
            if permission_id.startswith("app.") and normalize_app_name(permission_id.removeprefix("app.")) == normalized:
                return enabled
        return False

    def _load(self) -> dict[str, bool]:
        values = dict(DEFAULT_PERMISSIONS)
        try:
            stored = json.loads(PERMISSION_FILE.read_text())
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return values
        if isinstance(stored, dict):
            values.update({key: value for key, value in stored.items() if isinstance(value, bool)})
        return values


permission_store = PermissionStore()


def normalize_app_name(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKC", value)
        if unicodedata.category(character) != "Cf"
    ).casefold().strip()


def bundle_id_for_pid(pid: int) -> str | None:
    try:
        result = subprocess.run(
            ["/usr/bin/lsappinfo", "info", "-only", "bundleid", "-app", str(pid)],
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    match = re.search(r'"CFBundleIdentifier"="([^"]+)"', result.stdout)
    return match.group(1) if match else None
