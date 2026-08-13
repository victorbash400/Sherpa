import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types

from backend.agents.sherpa_agent import sherpa_app


logger = logging.getLogger("sherpa.tasks")


@dataclass
class SherpaTask:
    id: str
    voice_session_id: str
    instruction: str
    status: str = "running"
    summary: str = ""
    worker: asyncio.Task[None] | None = field(default=None, repr=False)


class SherpaTaskManager:
    def __init__(self) -> None:
        self._sessions = InMemorySessionService()
        self._runner = Runner(app=sherpa_app, session_service=self._sessions)
        self._tasks: dict[str, SherpaTask] = {}
        self._event_queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}

    def subscribe(self, voice_session_id: str) -> asyncio.Queue[dict[str, Any]]:
        return self._event_queues.setdefault(voice_session_id, asyncio.Queue())

    def start(self, voice_session_id: str, instruction: str) -> SherpaTask:
        task = SherpaTask(
            id=f"task_{crypto_id()}",
            voice_session_id=voice_session_id,
            instruction=instruction,
        )
        self._tasks[task.id] = task
        task.worker = asyncio.create_task(self._run(task), name=task.id)
        logger.info("task.started task=%s voice_session=%s", task.id, voice_session_id)
        return task

    def get(self, task_id: str) -> SherpaTask | None:
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status != "running" or not task.worker:
            return False
        task.worker.cancel()
        return True

    async def close(self) -> None:
        workers = [task.worker for task in self._tasks.values() if task.worker]
        for worker in workers:
            if not worker.done():
                worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)

    async def _run(self, task: SherpaTask) -> None:
        worker_session_id = f"{task.voice_session_id}:{task.id}"
        try:
            await self._sessions.create_session(
                app_name="sherpa",
                user_id="local-user",
                session_id=worker_session_id,
            )
            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=task.instruction)],
            )
            response_text = ""
            seen_calls: set[str] = set()
            seen_responses: set[str] = set()
            async for event in self._runner.run_async(
                user_id="local-user",
                session_id=worker_session_id,
                new_message=message,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                if event.error_message:
                    raise RuntimeError(event.error_message)
                for call in event.get_function_calls():
                    call_id = call.id or call.name
                    if call_id in seen_calls:
                        continue
                    seen_calls.add(call_id)
                    await self._emit(task, {
                        "type": "tool_call",
                        "id": call_id,
                        "name": call.name,
                        "args": call.args or {},
                        "message": describe_tool(call.name, call.args or {}),
                    })
                for response in event.get_function_responses():
                    response_id = response.id or response.name
                    if response_id in seen_responses:
                        continue
                    seen_responses.add(response_id)
                    failed = tool_failed(response.response)
                    await self._emit(task, {
                        "type": "tool_response",
                        "id": response_id,
                        "name": response.name,
                        "result": {"status": "failed" if failed else "done"},
                        "message": describe_result(response.name, failed),
                    })
                if event.content:
                    for part in event.content.parts or []:
                        if part.text and not part.thought:
                            response_text = merge_stream_text(response_text, part.text)
            task.status = "completed"
            task.summary = response_text.strip() or "Sherpa finished the task."
            await self._emit(task, {
                "type": "task_completed",
                "task_id": task.id,
                "message": task.summary,
            })
        except asyncio.CancelledError:
            task.status = "cancelled"
            task.summary = "Sherpa stopped the task."
            await self._emit(task, {
                "type": "task_cancelled",
                "task_id": task.id,
                "message": task.summary,
            })
        except Exception as error:
            task.status = "failed"
            task.summary = str(error)
            logger.exception("task.failed task=%s", task.id)
            await self._emit(task, {
                "type": "task_failed",
                "task_id": task.id,
                "message": f"Sherpa could not finish: {error}",
            })

    async def _emit(self, task: SherpaTask, event: dict[str, Any]) -> None:
        event["task_id"] = task.id
        await self.subscribe(task.voice_session_id).put(event)


sherpa_tasks = SherpaTaskManager()


async def delegate_task(instruction: str, tool_context: ToolContext) -> dict[str, str]:
    """Start the Sherpa agent on a macOS task and return immediately."""
    task = sherpa_tasks.start(tool_context.session.id, instruction)
    return {"status": "started", "task_id": task.id}


async def get_task_status(task_id: str, tool_context: ToolContext) -> dict[str, str]:
    """Return the current state of a delegated Sherpa task."""
    del tool_context
    task = sherpa_tasks.get(task_id)
    if not task:
        return {"status": "not_found", "task_id": task_id}
    return {"status": task.status, "task_id": task.id, "summary": task.summary}


async def cancel_task(task_id: str, tool_context: ToolContext) -> dict[str, str]:
    """Cancel a running Sherpa task."""
    del tool_context
    cancelled = sherpa_tasks.cancel(task_id)
    return {"status": "cancelled" if cancelled else "not_running", "task_id": task_id}


def crypto_id() -> str:
    import uuid
    return uuid.uuid4().hex


def tool_failed(response: dict | None) -> bool:
    return bool(response and (
        response.get("isError")
        or response.get("error")
        or response.get("status") == "failed"
    ))


def describe_tool(name: str, args: dict[str, Any]) -> str:
    target = next((args[key] for key in ("name", "app", "app_target", "query")
                   if isinstance(args.get(key), str) and args[key]), "")
    action = args.get("action")
    if name == "computer_app" and action in {"launch", "open"}:
        return f"Opening {target or 'the application'}"
    if name in {"computer_see", "computer_inspect_ui"}:
        return f"Checking {target or 'the screen'}"
    if name == "computer_click":
        return f"Clicking {target or 'the control'}"
    if name == "computer_type":
        return "Typing"
    if name == "computer_scroll":
        return "Scrolling"
    if name == "computer_press":
        return "Pressing a key"
    return name.removeprefix("computer_").replace("_", " ").capitalize()


def describe_result(name: str, failed: bool) -> str:
    action = name.removeprefix("computer_").replace("_", " ")
    return f"{action.capitalize()} {'failed' if failed else 'finished'}"


def merge_stream_text(current: str, incoming: str) -> str:
    """Merge ADK text deltas without repeating a cumulative final message."""
    if not incoming or current.endswith(incoming):
        return current
    if incoming.startswith(current):
        return incoming
    return current + incoming
