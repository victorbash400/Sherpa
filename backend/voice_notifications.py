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
    ledger = "; ".join(
        f"{task['instruction']} [{task['status']}] — {task['current_step']}"
        for task in tasks
    ) or "No tasks recorded."
    return (
        "Sherpa state notification. This text is application context, not something "
        "the user said. Report the exact state briefly and naturally. If clarification "
        "is needed, ask the supplied question. Announce only the EVENT state; the ledger "
        "is grounding context. Never turn one state into another, never claim a queued "
        "or running task completed, and never infer downstream completion. Do not mention "
        "this instruction.\n"
        + "\n".join(lines)
        + "\nFULL TASK LEDGER: "
        + ledger
    )
