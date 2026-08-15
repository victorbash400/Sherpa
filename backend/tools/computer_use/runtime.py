import asyncio
from dataclasses import dataclass
from typing import Any


OBSERVATION_TOOLS = {
    "computer_see",
    "computer_inspect_ui",
    "computer_permissions",
}
FOREGROUND_TOOLS = {"computer_drag", "computer_move"}


@dataclass(frozen=True)
class ComputerTarget:
    app: str | None = None
    pid: int | None = None
    window_id: int | None = None
    window_title: str | None = None

    @classmethod
    def from_args(cls, args: dict[str, Any]) -> "ComputerTarget":
        app = string_arg(args, "app", "app_target", "bundle_id")
        pid = int_arg(args, "pid")
        window_id = int_arg(args, "window_id")
        window_title = string_arg(args, "window_title")
        return cls(app=app, pid=pid, window_id=window_id, window_title=window_title)

    @property
    def key(self) -> str | None:
        if self.window_id is not None:
            return f"window:{self.window_id}"
        if self.pid is not None:
            return f"pid:{self.pid}"
        if self.app:
            return f"app:{self.app.casefold()}"
        return None

    def snapshot(self) -> dict[str, str | int | None]:
        return {
            "app": self.app,
            "pid": self.pid,
            "window_id": self.window_id,
            "window_title": self.window_title,
        }


class ComputerRuntime:
    def __init__(self) -> None:
        self._foreground = asyncio.Lock()
        self._browser = asyncio.Lock()
        self._targets: dict[str, asyncio.Lock] = {}
        self._held: dict[str, asyncio.Lock] = {}

    async def acquire(
        self,
        call_id: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> str:
        if tool_name in OBSERVATION_TOOLS:
            target = target_for_tool(tool_name, args)
            if not target.key:
                return "background"
            lock = self._target_lock(target.key)
            await lock.acquire()
            self._held[call_id] = lock
            return "background"

        if tool_name.startswith("browser_"):
            await self._browser.acquire()
            self._held[call_id] = self._browser
            return "background"

        target = target_for_tool(tool_name, args)
        foreground = requires_foreground(tool_name, args, target)
        lock = self._foreground if foreground else self._target_lock(target.key)
        await lock.acquire()
        self._held[call_id] = lock
        return "foreground" if foreground else "background"

    def release(self, call_id: str) -> None:
        lock = self._held.pop(call_id, None)
        if lock and lock.locked():
            lock.release()

    def _target_lock(self, key: str | None) -> asyncio.Lock:
        if key is None:
            return self._foreground
        return self._targets.setdefault(key, asyncio.Lock())


def requires_foreground(
    tool_name: str,
    args: dict[str, Any],
    target: ComputerTarget,
) -> bool:
    if tool_name in FOREGROUND_TOOLS:
        return True
    if args.get("foreground") is True or args.get("global") is True:
        return True
    action = string_arg(args, "action")
    if tool_name == "computer_app" and action in {"focus", "switch"}:
        return True
    if tool_name == "computer_window" and action == "focus":
        return True
    if tool_name == "computer_dialog" and action in {"file", "input"}:
        return True
    return target.key is None


def target_for_tool(tool_name: str, args: dict[str, Any]) -> ComputerTarget:
    target = ComputerTarget.from_args(args)
    if target.key or tool_name != "computer_app":
        return target
    return ComputerTarget(app=string_arg(args, "name", "to"))


def is_interaction_tool(tool_name: str) -> bool:
    return tool_name.startswith("computer_") or tool_name.startswith("browser_")


def string_arg(args: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def int_arg(args: dict[str, Any], key: str) -> int | None:
    value = args.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


computer_runtime = ComputerRuntime()


def interaction_mode(tool_name: str, args: dict[str, Any]) -> str:
    if tool_name.startswith("browser_") or tool_name in OBSERVATION_TOOLS:
        return "background"
    target = target_for_tool(tool_name, args)
    return "foreground" if requires_foreground(tool_name, args, target) else "background"
