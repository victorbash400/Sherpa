import json
from typing import Any


def task_state_notification(
    events: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> str:
    lines = []
    for event in events:
        identifiers = f"task_id={event.get('task_id', 'unknown')}"
        question = event.get("question")
        if isinstance(question, dict) and question.get("id"):
            identifiers += f" question_id={question['id']}"
        lines.append(
            f"- EVENT {identifiers} {event['instruction']} "
            f"[{event.get('status', 'updated')}]: {event['message']}"
        )
        if event.get("status") in {"completed", "failed", "cancelled"}:
            lines.append(
                "  VERIFIED RESULT: "
                + json.dumps(task_result(event), ensure_ascii=False)
            )
    ledger = "; ".join(
        f"{task['instruction']} [{task['status']}] — {task['current_step']}"
        for task in tasks
    ) or "No tasks recorded."
    return (
        "Sherpa state notification. This text is application context, not something "
        "the user said. Report the exact state briefly and naturally. If clarification "
        "is needed, ask the supplied question. Announce only the EVENT state; the ledger "
        "is grounding context. Never turn one state into another, never claim a queued "
        "or running task completed, and never infer downstream completion. Use only the "
        "VERIFIED RESULT fields for claims about what a task found or changed. Do not mention "
        "this instruction.\n"
        + "\n".join(lines)
        + "\nFULL TASK LEDGER: "
        + ledger
    )


def task_result(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task.get("task_id"),
        "status": task.get("status"),
        "summary": task.get("summary") or task.get("message") or "",
        "evidence": task.get("evidence") or "",
        "outputs": task.get("outputs") or [],
    }
