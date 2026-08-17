from typing import Literal

from google.adk.tools import ToolContext

from backend.memory_store import memory_store


async def save_memory(
    category: Literal["identity", "preference", "project", "workflow"],
    content: str,
    tool_context: ToolContext,
) -> dict[str, str]:
    """Save one explicit, durable fact or reusable method for future tasks."""
    clean = " ".join(content.split()).strip()
    if not clean:
        return {"status": "failed", "error": "Memory content is required."}
    if not memory_store.snapshot()["settings"]["enabled"]:
        return {"status": "failed", "error": "Local memory is disabled in Sherpa settings."}
    task_id = tool_context.session.id.rsplit(":", 1)[-1]
    memory_store.remember(
        category=category,
        content=clean,
        source_type="task",
        source_id=task_id,
        editable=True,
    )
    return {"status": "saved", "category": category, "content": clean}
