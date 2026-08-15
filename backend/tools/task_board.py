from typing import Literal

from google.adk.tools import ToolContext


TaskPhase = Literal["starting", "planning", "working", "checking", "blocked"]


def update_task_board(
    message: str,
    progress: int,
    phase: TaskPhase,
    tool_context: ToolContext,
    next_step: str = "",
) -> dict[str, object]:
    """Write a concise, truthful progress update for the current delegated task.

    Args:
        message: A standalone update describing what was learned, changed, or verified. Include enough context for another agent to understand it without reading earlier updates. Never write filler such as "working" or "task started".
        progress: Estimated completion from 0 through 95. Never report 100; completion is verified by the task runner.
        phase: The current task phase.
        next_step: What you will do next. Leave empty only when blocked or ready to provide the final response.
    """
    del tool_context
    return {
        "status": "recorded",
        "message": message.strip(),
        "progress": max(0, min(95, progress)),
        "phase": phase,
        "next_step": next_step.strip(),
    }
