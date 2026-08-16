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


def complete_task(
    summary: str,
    evidence: str,
    tool_context: ToolContext,
    outputs: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Explicitly finish the current task after its outcome has been observed.

    Args:
        summary: A concise description of the completed outcome.
        evidence: What was observed that proves the requested outcome occurred.
        outputs: Concrete results the user or a later task may need. Each output has a name, type, value, and verification. Return an empty list only when the summary and evidence contain the complete result.
    """
    tool_context.actions.end_of_agent = True
    return {
        "status": "completed",
        "summary": summary.strip(),
        "evidence": evidence.strip(),
        "outputs": outputs or [],
    }


def ask_task_question(
    question: str,
    blocking: bool,
    tool_context: ToolContext,
    context: str = "",
) -> dict[str, object]:
    """Ask the user for information needed by the current task.

    Args:
        question: The single, specific question the user should answer.
        blocking: True when no safe useful work can continue without the answer.
        context: A concise explanation of the ambiguity or problem encountered.
    """
    if blocking:
        tool_context.actions.end_of_agent = True
    return {
        "status": "waiting_for_user" if blocking else "question_recorded",
        "question": question.strip(),
        "blocking": blocking,
        "context": context.strip(),
    }
