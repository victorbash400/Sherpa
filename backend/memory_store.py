import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


MEMORY_DIRECTORY = Path.home() / "Library" / "Application Support" / "Sherpa"
MEMORY_DATABASE = MEMORY_DIRECTORY / "memory.sqlite3"
SETTING_LIMITS = {
    "custom_instructions": 1200,
    "chat_style": 240,
    "response_style": 240,
}


class MemoryStore:
    def __init__(self) -> None:
        MEMORY_DIRECTORY.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(MEMORY_DATABASE)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled INTEGER NOT NULL DEFAULT 1,
                    learn_from_tools INTEGER NOT NULL DEFAULT 1,
                    custom_instructions TEXT NOT NULL DEFAULT '',
                    chat_style TEXT NOT NULL DEFAULT '',
                    response_style TEXT NOT NULL DEFAULT ''
                );
                INSERT OR IGNORE INTO memory_settings (id) VALUES (1);

                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    editable INTEGER NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(category, content)
                );
                """
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            settings = dict(connection.execute(
                "SELECT enabled, learn_from_tools, custom_instructions, chat_style, response_style "
                "FROM memory_settings WHERE id = 1"
            ).fetchone())
            memories = [dict(row) for row in connection.execute(
                "SELECT id, category, content, source_type, editable, active, updated_at "
                "FROM memories ORDER BY updated_at DESC"
            )]
        settings["enabled"] = bool(settings["enabled"])
        settings["learn_from_tools"] = bool(settings["learn_from_tools"])
        for memory in memories:
            memory["editable"] = bool(memory["editable"])
            memory["active"] = bool(memory["active"])
        return {"settings": settings, "memories": memories, "limits": SETTING_LIMITS}

    def update_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        allowed = {"enabled", "learn_from_tools", *SETTING_LIMITS}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"Unknown memory setting: {sorted(unknown)[0]}")
        updates: list[str] = []
        parameters: list[Any] = []
        for key, value in values.items():
            if key in SETTING_LIMITS:
                text = str(value).strip()
                if len(text) > SETTING_LIMITS[key]:
                    raise ValueError(f"{key} exceeds its character limit")
                value = text
            else:
                value = int(bool(value))
            updates.append(f"{key} = ?")
            parameters.append(value)
        if updates:
            with self._lock, self._connect() as connection:
                connection.execute(
                    f"UPDATE memory_settings SET {', '.join(updates)} WHERE id = 1",
                    parameters,
                )
        return self.snapshot()

    def remember(
        self,
        *,
        category: str,
        content: str,
        source_type: str,
        source_id: str,
        editable: bool,
    ) -> None:
        clean = " ".join(content.split())[:320]
        if not clean:
            return
        now = datetime.now(UTC).isoformat()
        import uuid

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memories (
                    id, category, content, source_type, source_id,
                    editable, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(category, content) DO UPDATE SET
                    source_type = excluded.source_type,
                    source_id = excluded.source_id,
                    updated_at = excluded.updated_at
                """,
                (
                    f"memory_{uuid.uuid4().hex}", category, clean, source_type,
                    source_id, int(editable), now, now,
                ),
            )

    def update_memory(self, memory_id: str, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT editable FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            if not row:
                raise KeyError(memory_id)
            updates: list[str] = []
            parameters: list[Any] = []
            if "content" in values:
                if not bool(row["editable"]):
                    raise PermissionError("This memory is managed by Sherpa")
                content = " ".join(str(values["content"]).split())
                if not content or len(content) > 320:
                    raise ValueError("Memory must contain between 1 and 320 characters")
                updates.append("content = ?")
                parameters.append(content)
            if "active" in values:
                updates.append("active = ?")
                parameters.append(int(bool(values["active"])))
            if not updates:
                raise ValueError("No memory changes supplied")
            updates.append("updated_at = ?")
            parameters.append(datetime.now(UTC).isoformat())
            parameters.append(memory_id)
            connection.execute(
                f"UPDATE memories SET {', '.join(updates)} WHERE id = ?", parameters
            )
        return self.snapshot()

    def delete_all(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM memories")

    def context_for(self, audience: str, limit: int = 8) -> str:
        snapshot = self.snapshot()
        settings = snapshot["settings"]
        if not settings["enabled"]:
            return ""
        lines = []
        if settings["custom_instructions"]:
            lines.append(f"Instructions: {settings['custom_instructions']}")
        if settings["chat_style"]:
            lines.append(f"Conversation style: {settings['chat_style']}")
        if settings["response_style"]:
            lines.append(f"Response style: {settings['response_style']}")
        memory_limit = 4 if audience == "voice" else limit
        lines.extend(
            f"{memory['category']}: {memory['content']}"
            for memory in snapshot["memories"]
            if memory["active"]
        )
        selected = lines[: 3 + memory_limit]
        if not selected:
            return ""
        return "Sherpa memory (use only when relevant):\n- " + "\n- ".join(selected)

    def learning_enabled(self, tool_assisted: bool) -> bool:
        settings = self.snapshot()["settings"]
        return bool(settings["enabled"] and (settings["learn_from_tools"] or not tool_assisted))


memory_store = MemoryStore()
