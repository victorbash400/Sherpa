from typing import Any

from backend.tools.google_tools.workspace_core import WorkspaceApiError, workspace_request


TASKS_API = "https://tasks.googleapis.com/tasks/v1"


async def workspace_tasks_list_tasklists(max_results: int = 100) -> dict[str, Any]:
    """List the connected user's Google Tasks lists."""
    result = await workspace_request(
        "GET",
        f"{TASKS_API}/users/@me/lists",
        params={"maxResults": max(1, min(100, max_results))},
    )
    return {"tasklists": result.get("items", [])}


async def workspace_tasks_create_tasklist(title: str) -> dict[str, Any]:
    """Create a Google Tasks list."""
    result = await workspace_request("POST", f"{TASKS_API}/users/@me/lists", json={"title": title})
    return {"tasklist": result}


async def workspace_tasks_update_tasklist(tasklist_id: str, title: str) -> dict[str, Any]:
    """Rename a Google Tasks list."""
    result = await workspace_request(
        "PATCH",
        f"{TASKS_API}/users/@me/lists/{tasklist_id}",
        json={"title": title},
    )
    return {"tasklist": result}


async def workspace_tasks_delete_tasklist(tasklist_id: str) -> dict[str, Any]:
    """Delete a Google Tasks list."""
    await workspace_request("DELETE", f"{TASKS_API}/users/@me/lists/{tasklist_id}")
    return {"tasklist_id": tasklist_id, "status": "deleted"}


async def workspace_tasks_list_tasks(
    tasklist_id: str = "@default",
    show_completed: bool = False,
    show_hidden: bool = False,
    max_results: int = 100,
) -> dict[str, Any]:
    """List tasks from a Google Tasks list."""
    result = await workspace_request(
        "GET",
        f"{TASKS_API}/lists/{tasklist_id}/tasks",
        params={
            "showCompleted": str(show_completed).lower(),
            "showHidden": str(show_hidden).lower(),
            "maxResults": max(1, min(100, max_results)),
        },
    )
    return {"tasks": result.get("items", [])}


async def workspace_tasks_create_task(
    title: str,
    tasklist_id: str = "@default",
    notes: str = "",
    due: str | None = None,
    parent_task_id: str | None = None,
) -> dict[str, Any]:
    """Create a Google Task, optionally with notes, a due timestamp, or a parent task."""
    payload: dict[str, Any] = {"title": title}
    if notes:
        payload["notes"] = notes
    if due:
        payload["due"] = due
    params = {"parent": parent_task_id} if parent_task_id else None
    result = await workspace_request(
        "POST",
        f"{TASKS_API}/lists/{tasklist_id}/tasks",
        params=params,
        json=payload,
    )
    return {"task": result}


async def workspace_tasks_update_task(
    task_id: str,
    tasklist_id: str = "@default",
    title: str | None = None,
    notes: str | None = None,
    due: str | None = None,
    completed: bool | None = None,
) -> dict[str, Any]:
    """Update a Google Task's content, due time, or completion state."""
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if notes is not None:
        payload["notes"] = notes
    if due is not None:
        payload["due"] = due
    if completed is not None:
        payload["status"] = "completed" if completed else "needsAction"
        if not completed:
            payload["completed"] = None
    if not payload:
        raise WorkspaceApiError("Provide at least one task field to update.")
    result = await workspace_request(
        "PATCH",
        f"{TASKS_API}/lists/{tasklist_id}/tasks/{task_id}",
        json=payload,
    )
    return {"task": result}


async def workspace_tasks_delete_task(task_id: str, tasklist_id: str = "@default") -> dict[str, Any]:
    """Delete a Google Task."""
    await workspace_request("DELETE", f"{TASKS_API}/lists/{tasklist_id}/tasks/{task_id}")
    return {"task_id": task_id, "status": "deleted"}


async def workspace_tasks_move_task(
    task_id: str,
    tasklist_id: str = "@default",
    parent_task_id: str | None = None,
    previous_task_id: str | None = None,
) -> dict[str, Any]:
    """Move a task within a list or make it a subtask."""
    params: dict[str, str] = {}
    if parent_task_id:
        params["parent"] = parent_task_id
    if previous_task_id:
        params["previous"] = previous_task_id
    result = await workspace_request(
        "POST",
        f"{TASKS_API}/lists/{tasklist_id}/tasks/{task_id}/move",
        params=params,
    )
    return {"task": result}


async def workspace_tasks_clear_completed(tasklist_id: str = "@default") -> dict[str, Any]:
    """Remove completed tasks from a Google Tasks list."""
    await workspace_request("POST", f"{TASKS_API}/lists/{tasklist_id}/clear")
    return {"tasklist_id": tasklist_id, "status": "completed_tasks_cleared"}


TASKS_TOOLS = [
    workspace_tasks_list_tasklists,
    workspace_tasks_create_tasklist,
    workspace_tasks_update_tasklist,
    workspace_tasks_delete_tasklist,
    workspace_tasks_list_tasks,
    workspace_tasks_create_task,
    workspace_tasks_update_task,
    workspace_tasks_delete_task,
    workspace_tasks_move_task,
    workspace_tasks_clear_completed,
]
