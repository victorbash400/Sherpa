import logging
from collections.abc import Awaitable, Callable

from google.genai import types

from backend.sherpa_tasks import sherpa_tasks


logger = logging.getLogger("sherpa.voice")
VoiceToolResponder = Callable[[str, str, dict], Awaitable[None]]


VOICE_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="submit_task",
            description="Hand one complete request to Sherpa. New work runs sequentially behind any active task.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "instruction": types.Schema(
                        type=types.Type.STRING,
                        description="The user's complete request, including every independent outcome and constraint.",
                    )
                },
                required=["instruction"],
            ),
        ),
        types.FunctionDeclaration(
            name="inspect_task",
            description="Read one task's exact status, verified summary, evidence, and structured outputs. Use before answering what that task found or changed.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"task_id": types.Schema(type=types.Type.STRING)},
                required=["task_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="list_active_tasks",
            description="List unfinished tasks with explicit running, queued, or blocked state. An empty result does not mean earlier tasks completed.",
            behavior=types.Behavior.BLOCKING,
        ),
        types.FunctionDeclaration(
            name="list_tasks",
            description="List every task with exact status and verified results. Use when the user asks what earlier work found, created, changed, or deleted and the task ID is uncertain.",
            behavior=types.Behavior.BLOCKING,
        ),
        types.FunctionDeclaration(
            name="cancel_task",
            description="Cancel one running Sherpa task when the user asks to stop it.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={"task_id": types.Schema(type=types.Type.STRING)},
                required=["task_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="update_task",
            description="Replace the stored instruction for a queued task that has not begun working.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "task_id": types.Schema(type=types.Type.STRING),
                    "instruction": types.Schema(type=types.Type.STRING),
                },
                required=["task_id", "instruction"],
            ),
        ),
        types.FunctionDeclaration(
            name="steer_task",
            description="Change running or blocked work at its next completed tool boundary.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "task_id": types.Schema(type=types.Type.STRING),
                    "instruction": types.Schema(type=types.Type.STRING),
                },
                required=["task_id", "instruction"],
            ),
        ),
        types.FunctionDeclaration(
            name="answer_task_question",
            description="Give a user's answer to an open question from a running Sherpa task.",
            behavior=types.Behavior.BLOCKING,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "task_id": types.Schema(type=types.Type.STRING),
                    "question_id": types.Schema(type=types.Type.STRING),
                    "answer": types.Schema(type=types.Type.STRING),
                },
                required=["task_id", "question_id", "answer"],
            ),
        ),
    ])
]


async def handle_voice_tool_call(
    call: types.FunctionCall,
    session_id: str,
    respond: VoiceToolResponder,
) -> None:
    call_id = call.id or call.name or "unknown"
    name = call.name or "unknown"
    args = call.args or {}
    logger.info("tool.requested session=%s call=%s name=%s", session_id, call_id, name)

    if name == "submit_task":
        instruction = str(args.get("instruction", "")).strip()
        if not instruction:
            await respond(call_id, name, {"error": "instruction is required"})
            return
        logger.info(
            'task.admission session=%s instruction="%s"',
            session_id,
            " ".join(instruction.split())[:1000],
        )
        decision = await sherpa_tasks.submit(session_id, instruction)
        logger.info(
            "task.receipt session=%s status=%s submission=%s call=%s",
            session_id,
            decision["status"],
            decision.get("submission_id", "none"),
            call_id,
        )
        await respond(call_id, name, decision)
        return

    if name == "inspect_task":
        task_id = str(args.get("task_id", "")).strip()
        task = sherpa_tasks.get(task_id)
        response = (
            sherpa_tasks.snapshot(task)
            if task and task.chat_id == session_id
            else {"status": "not_found", "task_id": task_id}
        )
        await respond(call_id, name, response)
        return

    if name == "list_active_tasks":
        tasks = [
            sherpa_tasks.snapshot(task)
            for task in sherpa_tasks.list_active_for_chat(session_id)
        ]
        submissions = [
            sherpa_tasks.submission_snapshot(submission)
            for submission in sherpa_tasks.list_pending_submissions(session_id)
        ]
        await respond(call_id, name, active_tasks_response(tasks, submissions))
        return

    if name == "list_tasks":
        tasks = [
            sherpa_tasks.snapshot(task)
            for task in sherpa_tasks.list_for_chat(session_id)
            if task.kind == "worker" or not task.child_ids
        ]
        submissions = [
            sherpa_tasks.submission_snapshot(submission)
            for submission in sherpa_tasks.list_pending_submissions(session_id)
        ]
        await respond(call_id, name, task_ledger_response(tasks, submissions))
        return

    if name == "cancel_task":
        task_id = str(args.get("task_id", "")).strip()
        task = sherpa_tasks.get(task_id)
        cancelled = bool(
            task and task.chat_id == session_id and sherpa_tasks.cancel(task_id)
        )
        await respond(call_id, name, {
            "status": "cancelled" if cancelled else "not_running",
            "task_id": task_id,
        })
        return

    if name in {"update_task", "steer_task"}:
        task_id = str(args.get("task_id", "")).strip()
        instruction = str(args.get("instruction", "")).strip()
        task = sherpa_tasks.get(task_id)
        response = (
            await (
                sherpa_tasks.update(task_id, instruction)
                if name == "update_task"
                else sherpa_tasks.steer(task_id, instruction)
            )
            if task and task.chat_id == session_id
            else {"status": "not_found", "task_id": task_id}
        )
        await respond(call_id, name, response)
        return

    if name == "answer_task_question":
        task_id = str(args.get("task_id", "")).strip()
        question_id = str(args.get("question_id", "")).strip()
        answer = str(args.get("answer", "")).strip()
        task = sherpa_tasks.get(task_id)
        response = (
            await sherpa_tasks.answer_question(task_id, question_id, answer)
            if task and task.chat_id == session_id
            else {"status": "not_found", "task_id": task_id}
        )
        await respond(call_id, name, response)
        return

    await respond(call_id, name, {"error": "Unknown voice tool"})


def active_tasks_response(tasks: list[dict], submissions: list[dict]) -> dict:
    if tasks:
        counts = {
            status: sum(task["status"] == status for task in tasks)
            for status in ("running", "queued", "blocked")
        }
        message = (
            f"{counts['running']} running, {counts['queued']} queued, "
            f"and {counts['blocked']} waiting for input."
        )
        spoken_summary = "Current tasks: " + "; ".join(
            f"{task['instruction']} [{task['status']}] — {task['current_step']}"
            for task in tasks
        )
    elif submissions:
        message = f"{len(submissions)} request(s) are still being organized."
        spoken_summary = "Sherpa is still organizing: " + "; ".join(
            submission["instruction"] for submission in submissions
        )
    else:
        message = "No tasks are currently active. This does not indicate that any task completed."
        spoken_summary = "No tasks are currently running. I cannot infer whether any earlier task completed from this check."
    return {
        "status": "active_tasks_found" if tasks else "no_active_tasks",
        "active_count": len(tasks),
        "received_count": len(submissions),
        "message": message,
        "spoken_summary": spoken_summary,
        "received": submissions,
        "tasks": tasks,
    }


def task_ledger_response(tasks: list[dict], submissions: list[dict]) -> dict:
    counts = {
        status: sum(task["status"] == status for task in tasks)
        for status in ("running", "completed", "failed", "cancelled")
    }
    entries = [
        *(f"{submission['instruction']} — received" for submission in submissions),
        *(task_spoken_result(task) for task in tasks),
    ]
    return {
        "status": "tasks_found" if tasks else "no_tasks",
        "counts": counts,
        "received": submissions,
        "spoken_summary": "; ".join(entries) if entries else "There are no tasks recorded in this conversation.",
        "tasks": tasks,
    }


def task_spoken_result(task: dict) -> str:
    status = task["status"]
    base = f"{task['instruction']} — {status}"
    if status not in {"completed", "failed", "cancelled"}:
        return f"{base}: {task['current_step']}"
    summary = str(task.get("summary") or task.get("current_step") or "").strip()
    evidence = str(task.get("evidence") or "").strip()
    outputs = task.get("outputs") or []
    details = "; ".join(part for part in (
        summary,
        f"Evidence: {evidence}" if evidence else "",
        f"Outputs: {outputs}" if outputs else "",
    ) if part)
    return f"{base}: {details}" if details else base
