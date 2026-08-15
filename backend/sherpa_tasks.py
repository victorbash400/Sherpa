import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types

from backend.agents.sherpa_agent import sherpa_app
from backend.agents.task_coordinator import task_coordinator_app
from backend.memory_manager import memory_manager
from backend.memory_store import memory_store
from backend.permission_store import permission_store
from backend.task_graph import AdmissionDecision, WorkerAssignment
from backend.task_graph import dependency_context, validate_admission_decision
from backend.tools.computer_use.runtime import ComputerTarget, interaction_mode
from backend.tools.google_tools import run_with_google_tool_scope


logger = logging.getLogger("sherpa.tasks")
PEEKABOO_ELEMENT_LINE = re.compile(
    r'^\s*(?P<id>\S+)\s+-\s+.*?\s+-\s+at\s+'
    r'\((?P<x>-?\d+(?:\.\d+)?),\s*(?P<y>-?\d+(?:\.\d+)?)\)\s+'
    r'size\s+(?P<width>\d+(?:\.\d+)?)\s*[×x]\s*(?P<height>\d+(?:\.\d+)?)',
    re.MULTILINE,
)
BROWSER_BOX = re.compile(
    r'\[ref=(?P<ref>[^\]]+)\].*?\[box=(?P<x>-?\d+(?:\.\d+)?),'
    r'(?P<y>-?\d+(?:\.\d+)?),(?P<width>\d+(?:\.\d+)?),'
    r'(?P<height>\d+(?:\.\d+)?)\]'
)


class TaskSteeringBoundary(Exception):
    def __init__(self, directive: dict[str, Any]) -> None:
        self.directive = directive


class TaskQuestionBoundary(Exception):
    def __init__(self, question: dict[str, Any]) -> None:
        self.question = question


@dataclass
class SherpaTask:
    id: str
    chat_id: str
    instruction: str
    request: str = ""
    kind: str = "coordinator"
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)
    dependency_ids: list[str] = field(default_factory=list)
    capabilities: tuple[str, ...] = ()
    status: str = "running"
    phase: str = "starting"
    progress: int = 0
    current_step: str = "Waiting to start"
    summary: str = ""
    evidence: str = ""
    preview_target: dict[str, str | int | None] | None = None
    interaction_mode: str = "background"
    updates: list[dict[str, Any]] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)
    directives: asyncio.Queue[dict[str, Any]] = field(
        default_factory=asyncio.Queue,
        repr=False,
    )
    worker: asyncio.Task[None] | None = field(default=None, repr=False)


@dataclass
class SherpaSubmission:
    id: str
    chat_id: str
    instruction: str
    status: str = "received"
    decision: str = "pending"
    message: str = "Sherpa received the request."
    task_id: str | None = None
    worker: asyncio.Task[None] | None = field(default=None, repr=False)


class SherpaTaskManager:
    def __init__(self) -> None:
        self._sessions = InMemorySessionService()
        self._runner = Runner(app=sherpa_app, session_service=self._sessions)
        self._coordinator_runner = Runner(app=task_coordinator_app, session_service=self._sessions)
        self._tasks: dict[str, SherpaTask] = {}
        self._submissions: dict[str, SherpaSubmission] = {}
        self._event_queues: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._admission_lease = asyncio.Lock()

    def subscribe(self, chat_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._event_queues.setdefault(chat_id, set()).add(queue)
        return queue

    def unsubscribe(self, chat_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subscribers = self._event_queues.get(chat_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._event_queues.pop(chat_id, None)

    async def submit(self, chat_id: str, instruction: str) -> dict[str, Any]:
        if not permission_store.enabled("google.models"):
            return {
                "status": "resolved",
                "submission_id": None,
                "instruction": instruction,
                "decision": "failed",
                "message": "Gemini models are turned off in Sherpa Plugins.",
                "task_id": None,
            }
        normalized = " ".join(instruction.lower().split())
        existing = next((
            submission
            for submission in reversed(self._submissions.values())
            if submission.chat_id == chat_id
            and submission.status == "received"
            and " ".join(submission.instruction.lower().split()) == normalized
        ), None)
        if existing:
            return self.submission_snapshot(existing)

        submission = SherpaSubmission(
            id=f"submission_{crypto_id()}",
            chat_id=chat_id,
            instruction=instruction,
        )
        self._submissions[submission.id] = submission
        submission.worker = asyncio.create_task(
            self._process_submission(submission),
            name=submission.id,
        )
        logger.info("submission.received submission=%s chat=%s", submission.id, chat_id)
        return self.submission_snapshot(submission)

    async def _process_submission(self, submission: SherpaSubmission) -> None:
        try:
            async with self._admission_lease:
                admission = await self._admit(submission.chat_id, submission.instruction)
                await self._resolve_submission(submission, admission)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            submission.status = "resolved"
            submission.decision = "failed"
            submission.message = f"Sherpa could not evaluate the request: {error}"
            logger.exception("submission.failed submission=%s", submission.id)
            await self._emit_chat(submission.chat_id, {
                "type": "submission_updated",
                **self.submission_snapshot(submission),
            })

    async def _resolve_submission(
        self,
        submission: SherpaSubmission,
        admission: AdmissionDecision,
    ) -> None:
        validate_admission_decision(admission)
        submission.status = "resolved"
        submission.decision = admission.decision
        submission.message = admission.message
        if admission.decision == "already_active":
            existing = self._tasks.get(admission.existing_task_id or "")
            if (
                not existing
                or existing.chat_id != submission.chat_id
                or existing.status != "running"
            ):
                raise RuntimeError("Sherpa returned an invalid active task reference.")
            submission.task_id = existing.id
        elif admission.decision == "accepted":
            task = SherpaTask(
                id=f"task_{crypto_id()}",
                chat_id=submission.chat_id,
                instruction=submission.instruction,
                request=submission.instruction,
            )
            self._tasks[task.id] = task
            submission.task_id = task.id
            task.phase = "planning"
            task.current_step = "Organizing the work"
            task.worker = asyncio.create_task(
                self._dispatch(task, admission.assignments),
                name=task.id,
            )
            self._emit_nowait(task, {"type": "task_started", **self.snapshot(task)})
            logger.info("task.started task=%s chat=%s", task.id, submission.chat_id)
        await self._emit_chat(submission.chat_id, {
            "type": "submission_updated",
            **self.submission_snapshot(submission),
        })
        logger.info(
            "submission.resolved submission=%s decision=%s task=%s",
            submission.id,
            submission.decision,
            submission.task_id or "none",
        )

    def get(self, task_id: str) -> SherpaTask | None:
        return self._tasks.get(task_id)

    def list_for_chat(self, chat_id: str) -> list[SherpaTask]:
        return [
            task for task in reversed(self._tasks.values())
            if task.chat_id == chat_id
        ]

    def list_active_for_chat(self, chat_id: str) -> list[SherpaTask]:
        return [
            task
            for task in self.list_for_chat(chat_id)
            if task.status == "running"
            and (task.kind == "worker" or not task.child_ids)
        ]

    def list_pending_submissions(self, chat_id: str) -> list[SherpaSubmission]:
        return [
            submission
            for submission in self._submissions.values()
            if submission.chat_id == chat_id and submission.status == "received"
        ]

    def submission_snapshot(self, submission: SherpaSubmission) -> dict[str, Any]:
        return {
            "status": submission.status,
            "submission_id": submission.id,
            "instruction": submission.instruction,
            "decision": submission.decision,
            "message": submission.message,
            "task_id": submission.task_id,
        }

    def snapshot(self, task: SherpaTask) -> dict[str, Any]:
        snapshot = {
            "task_id": task.id,
            "chat_id": task.chat_id,
            "instruction": task.instruction,
            "request": task.request,
            "kind": task.kind,
            "parent_id": task.parent_id,
            "child_ids": list(task.child_ids),
            "dependency_ids": list(task.dependency_ids),
            "capabilities": list(task.capabilities),
            "status": task.status,
            "phase": task.phase,
            "progress": task.progress,
            "current_step": task.current_step,
            "summary": task.summary,
            "evidence": task.evidence,
            "preview_target": task.preview_target,
            "interaction_mode": task.interaction_mode,
            "updates": list(task.updates),
            "questions": list(task.questions),
        }
        snapshot["children"] = [
            self.snapshot(child)
            for child_id in task.child_ids
            if (child := self._tasks.get(child_id))
        ]
        return snapshot

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status != "running":
            return False
        self._mark_cancelled(task)
        if task.worker and task.worker is not asyncio.current_task():
            task.worker.cancel()
        return True

    async def steer(self, task_id: str, instruction: str) -> dict[str, Any]:
        task = self._tasks.get(task_id)
        clean_instruction = " ".join(instruction.split()).strip()
        if not task or task.status != "running":
            return {"status": "not_running", "task_id": task_id}
        if not clean_instruction:
            return {"status": "invalid", "task_id": task_id}
        directive = {
            "type": "steer",
            "id": f"directive_{crypto_id()}",
            "instruction": clean_instruction,
            "created_at": datetime.now(UTC).isoformat(),
        }
        await task.directives.put(directive)
        self._record_update(
            task,
            "working",
            task.progress,
            f"Direction changed: {clean_instruction}",
            "Applying the change after the current action.",
        )
        await self._emit(task, {"type": "task_steering_queued", **self.snapshot(task)})
        return {"status": "queued", "task_id": task_id, "directive_id": directive["id"]}

    async def answer_question(
        self,
        task_id: str,
        question_id: str,
        answer: str,
    ) -> dict[str, Any]:
        task = self._tasks.get(task_id)
        clean_answer = " ".join(answer.split()).strip()
        question = next(
            (item for item in task.questions if item["id"] == question_id),
            None,
        ) if task else None
        if not task or task.status != "running":
            return {"status": "not_running", "task_id": task_id}
        if not question or question["status"] != "open":
            return {"status": "question_not_open", "task_id": task_id}
        if not clean_answer:
            return {"status": "invalid", "task_id": task_id}
        question["status"] = "answered"
        question["answer"] = clean_answer
        await task.directives.put({
            "type": "answer",
            "id": f"directive_{crypto_id()}",
            "question_id": question_id,
            "question": question["question"],
            "answer": clean_answer,
            "created_at": datetime.now(UTC).isoformat(),
        })
        await self._emit(task, {"type": "task_question_answered", **self.snapshot(task)})
        return {"status": "queued", "task_id": task_id, "question_id": question_id}

    async def close(self) -> None:
        workers = [
            worker
            for worker in (
                *(task.worker for task in self._tasks.values()),
                *(submission.worker for submission in self._submissions.values()),
            )
            if worker
        ]
        for worker in workers:
            if not worker.done():
                worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)

    async def _admit(self, chat_id: str, instruction: str) -> AdmissionDecision:
        admission_id = f"{chat_id}:admission:{crypto_id()}"
        active_tasks = [
            {
                "task_id": task.id,
                "request": task.request or task.instruction,
                "phase": task.phase,
                "current_step": task.current_step,
            }
            for task in self.list_for_chat(chat_id)
            if task.status == "running" and task.parent_id is None
        ]
        await self._sessions.create_session(
            app_name="task_coordinator",
            user_id="local-user",
            session_id=admission_id,
        )
        response_text = ""
        prompt = json.dumps({
            "requested_work": instruction,
            "active_tasks": active_tasks,
            "relevant_memory": memory_store.context_for("coordinator", limit=5),
        })
        async for event in self._coordinator_runner.run_async(
            user_id="local-user",
            session_id=admission_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ):
            if event.error_message:
                raise RuntimeError(event.error_message)
            if event.content:
                for part in event.content.parts or []:
                    if part.text and not part.thought:
                        response_text = merge_stream_text(response_text, part.text)
        return AdmissionDecision.model_validate_json(response_text)

    async def _dispatch(
        self,
        task: SherpaTask,
        assignments: list[WorkerAssignment],
    ) -> None:
        try:
            if len(assignments) == 1:
                assignment = assignments[0]
                task.kind = "worker"
                task.instruction = assignment.title
                task.capabilities = tuple(assignment.tools)
                await self._run_worker(task, assignment.instruction)
                return

            assignment_by_key = {assignment.key: assignment for assignment in assignments}
            child_by_key = {
                assignment.key: self._create_worker(task, assignment)
                for assignment in assignments
            }
            child_tasks = list(child_by_key.values())
            task.child_ids = [child.id for child in child_tasks]
            for assignment in assignments:
                child_by_key[assignment.key].dependency_ids = [
                    child_by_key[key].id for key in assignment.depends_on
                ]
            for child in child_tasks:
                self._emit_nowait(child, {"type": "task_started", **self.snapshot(child)})
            titles = ", ".join(assignment.title for assignment in assignments)
            self._record_update(
                task,
                "working",
                5,
                f"Sherpa separated the request into {len(child_tasks)} tasks: {titles}.",
                "Ready assignments are running in parallel.",
            )
            await self._emit(task, {"type": "task_updated", **self.snapshot(task)})
            await self._run_assignment_graph(assignment_by_key, child_by_key)

            failed = [child for child in child_tasks if child.status == "failed"]
            cancelled = [child for child in child_tasks if child.status == "cancelled"]
            task.progress = 100
            if failed:
                task.status = "failed"
                task.phase = "failed"
            elif cancelled:
                task.status = "cancelled"
                task.phase = "cancelled"
            else:
                task.status = "completed"
                task.phase = "completed"
            task.summary = "\n".join(
                f"- **{child.instruction}:** {child.summary}" for child in child_tasks
            )
            task.current_step = task.summary
            await self._emit(task, {
                "type": f"task_{task.status}",
                "message": task.summary,
                **self.snapshot(task),
            })
        except asyncio.CancelledError:
            for child_id in task.child_ids:
                child = self._tasks.get(child_id)
                if child and child.status == "running":
                    self.cancel(child.id)
            if task.status != "cancelled":
                self._mark_cancelled(task)
        except Exception as error:
            task.status = "failed"
            task.phase = "failed"
            task.summary = str(error)
            task.current_step = task.summary
            logger.exception("task.planning_failed task=%s", task.id)
            await self._emit(task, {
                "type": "task_failed",
                "message": f"Sherpa could not organize the work: {error}",
                **self.snapshot(task),
            })

    def _create_worker(
        self,
        parent: SherpaTask,
        assignment: WorkerAssignment,
    ) -> SherpaTask:
        child = SherpaTask(
            id=f"task_{crypto_id()}",
            chat_id=parent.chat_id,
            instruction=assignment.title,
            request=assignment.instruction,
            kind="worker",
            parent_id=parent.id,
            capabilities=tuple(assignment.tools),
            phase="queued",
            current_step="Waiting for prerequisite work" if assignment.depends_on else "Ready to start",
        )
        self._tasks[child.id] = child
        return child

    def _start_created_worker(self, child: SherpaTask, instruction: str) -> None:
        child.worker = asyncio.create_task(
            self._run_worker(child, instruction),
            name=child.id,
        )

    async def _run_assignment_graph(
        self,
        assignments: dict[str, WorkerAssignment],
        children: dict[str, SherpaTask],
    ) -> None:
        pending = set(assignments)
        running: dict[str, asyncio.Task[None]] = {}
        completed: dict[str, tuple[str, str, str]] = {}

        while pending or running:
            for key in tuple(pending):
                assignment = assignments[key]
                child = children[key]
                dependencies = [children[item] for item in assignment.depends_on]
                if child.status == "cancelled":
                    pending.remove(key)
                    continue
                blocked = next(
                    (dependency for dependency in dependencies if dependency.status in {"failed", "cancelled"}),
                    None,
                )
                if blocked:
                    child.status = "failed"
                    child.phase = "failed"
                    child.summary = f"Did not start because {blocked.instruction} did not complete."
                    child.current_step = child.summary
                    pending.remove(key)
                    await self._emit(child, {
                        "type": "task_failed",
                        "message": child.summary,
                        **self.snapshot(child),
                    })
                    continue
                if not all(dependency.status == "completed" for dependency in dependencies):
                    continue
                instruction = dependency_context(assignment, completed)
                self._start_created_worker(child, instruction)
                if child.worker:
                    running[key] = child.worker
                pending.remove(key)

            if not running:
                if pending:
                    raise RuntimeError("Sherpa's task graph could not make progress.")
                break

            done, _ = await asyncio.wait(
                tuple(running.values()),
                return_when=asyncio.FIRST_COMPLETED,
            )
            for key, worker in tuple(running.items()):
                if worker not in done:
                    continue
                await worker
                child = children[key]
                if child.status == "completed":
                    completed[key] = (child.instruction, child.summary, child.evidence)
                running.pop(key)

    def _mark_cancelled(self, task: SherpaTask) -> None:
        task.status = "cancelled"
        task.phase = "cancelled"
        task.summary = "Sherpa stopped the task."
        task.current_step = task.summary
        self._emit_nowait(task, {
            "type": "task_cancelled",
            "message": task.summary,
            **self.snapshot(task),
        })

    async def _run_worker(self, task: SherpaTask, instruction: str) -> None:
        next_instruction = instruction
        resume = False
        while task.status == "running":
            try:
                await self._run_with_computer(
                    task,
                    next_instruction,
                    resume=resume,
                )
                return
            except TaskQuestionBoundary as boundary:
                directives = await self._wait_for_answer(task, boundary.question["id"])
                next_instruction = await self._directive_prompt(task, directives)
                resume = True

    async def _run_with_computer(
        self,
        task: SherpaTask,
        instruction: str,
        *,
        resume: bool = False,
    ) -> None:
        worker_session_id = f"{task.chat_id}:{task.id}"
        try:
            task.phase = "starting"
            task.current_step = "Starting work"
            await self._emit(task, {"type": "task_updated", **self.snapshot(task)})
            if not resume:
                await self._sessions.create_session(
                    app_name="sherpa",
                    user_id="local-user",
                    session_id=worker_session_id,
                )
            memory_context = memory_store.context_for("sherpa") if not resume else ""
            worker_prompt = (
                f"{memory_context}\n\nAssigned task:\n{instruction}"
                if memory_context else instruction
            )
            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=worker_prompt)],
            )
            response_text = ""
            seen_calls: set[str] = set()
            seen_responses: set[str] = set()
            tool_call_args: dict[str, dict[str, Any]] = {}
            element_targets: dict[str, tuple[float, float]] = {}
            browser_targets: dict[str, tuple[float, float]] = {}
            browser_elements: list[dict[str, Any]] = []
            result_sequence = 0
            last_successful_action = -1
            last_successful_observation = -1
            completion: dict[str, Any] | None = None
            async for event in run_with_google_tool_scope(
                self._runner,
                f"{task.request}\n{instruction}",
                capabilities=task.capabilities,
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
                    if call.name == "update_task_board":
                        args = call.args or {}
                        self._record_update(
                            task,
                            str(args.get("phase", "working")),
                            int(args.get("progress", task.progress)),
                            str(args.get("message", "Working")),
                            str(args.get("next_step", "")),
                        )
                        await self._emit(task, {
                            "type": "task_updated",
                            **self.snapshot(task),
                        })
                        continue
                    intent = task.current_step
                    event_args = dict(call.args or {})
                    tool_call_args[call_id] = event_args
                    if call.name.startswith("browser_"):
                        if not browser_elements:
                            browser_elements = await chrome_accessibility_elements()
                        target = browser_overlay_target(
                            call.name,
                            event_args,
                            browser_targets,
                            browser_elements,
                        )
                    else:
                        target = overlay_target(event_args, element_targets)
                    if target:
                        event_args["overlay_x"], event_args["overlay_y"] = target
                        logger.info(
                            "overlay.target task=%s element=%s x=%.1f y=%.1f",
                            task.id,
                            event_args.get("on") or event_args.get("target"),
                            target[0],
                            target[1],
                        )
                    elif call.name in {"computer_click", "browser_click"}:
                        logger.warning(
                            "overlay.target_missing task=%s element=%s cached=%d",
                            task.id,
                            event_args.get("on") or event_args.get("target"),
                            len(element_targets) + len(browser_targets),
                        )
                    task.current_step = describe_tool(call.name, event_args)
                    preview_target = preview_target_for(call.name, event_args)
                    if preview_target:
                        task.preview_target = preview_target
                        task.interaction_mode = interaction_mode(call.name, event_args)
                    await self._emit(task, {
                        "type": "tool_call",
                        "id": call_id,
                        "name": call.name,
                        "args": event_args,
                        "message": describe_tool(call.name, event_args),
                        "intent": intent,
                        "interaction_mode": task.interaction_mode,
                        "preview_target": preview_target,
                    })
                for response in event.get_function_responses():
                    response_id = response.id or response.name
                    if response_id in seen_responses:
                        continue
                    seen_responses.add(response_id)
                    if response.name == "update_task_board":
                        directive = self._take_directive(task)
                        if directive:
                            raise TaskSteeringBoundary(directive)
                        continue
                    if response.name == "ask_task_question":
                        payload = response.response or {}
                        question = {
                            "id": f"question_{crypto_id()}",
                            "question": str(payload.get("question", "")).strip(),
                            "context": str(payload.get("context", "")).strip(),
                            "blocking": bool(payload.get("blocking")),
                            "status": "open",
                            "created_at": datetime.now(UTC).isoformat(),
                        }
                        task.questions.append(question)
                        self._record_update(
                            task,
                            "blocked" if question["blocking"] else "working",
                            task.progress,
                            question["question"],
                            "Waiting for the user's answer." if question["blocking"] else "Continuing independent work.",
                        )
                        if question["blocking"]:
                            task.phase = "blocked"
                            task.current_step = question["question"]
                        await self._emit(task, {
                            "type": "task_question",
                            "question": question,
                            **self.snapshot(task),
                        })
                        if question["blocking"]:
                            raise TaskQuestionBoundary(question)
                    if response.name == "complete_task":
                        completion = dict(response.response or {})
                    if response.name in {"computer_see", "computer_inspect_ui"}:
                        element_targets = extract_element_targets(response.response)
                    if response.name.startswith("browser_"):
                        next_browser_targets = extract_browser_targets(response.response)
                        if next_browser_targets:
                            browser_targets = next_browser_targets
                    failed = tool_failed(response.response)
                    failure_message = tool_error_message(response.response) if failed else None
                    is_control_tool = response.name in {
                        "ask_task_question",
                        "complete_task",
                    }
                    if not is_control_tool:
                        result_sequence += 1
                    if not failed and not is_control_tool:
                        if is_observation_tool(response.name):
                            last_successful_observation = result_sequence
                        elif tool_result_self_verifies(
                            response.name,
                            tool_call_args.get(response_id, {}),
                        ):
                            last_successful_action = result_sequence
                            last_successful_observation = result_sequence
                        else:
                            last_successful_action = result_sequence
                    await self._emit(task, {
                        "type": "tool_response",
                        "id": response_id,
                        "name": response.name,
                        "result": {
                            "status": "failed" if failed else "done",
                            "error": failure_message,
                        },
                        "message": failure_message or describe_result(response.name, failed),
                    })
                    directive = self._take_directive(task)
                    if directive:
                        raise TaskSteeringBoundary(directive)
                if event.content:
                    for part in event.content.parts or []:
                        if part.text and not part.thought:
                            response_text = merge_stream_text(response_text, part.text)
            if not completion:
                raise RuntimeError(
                    "Sherpa stopped without explicitly completing the task."
                )
            if (
                last_successful_observation < 0
                or last_successful_observation < last_successful_action
            ):
                raise RuntimeError(
                    "Sherpa stopped without observing the result of its latest successful action."
                )
            task.status = "completed"
            task.phase = "completed"
            task.progress = 100
            task.summary = str(completion.get("summary", "")).strip()
            evidence = str(completion.get("evidence", "")).strip()
            if not task.summary or not evidence:
                raise RuntimeError("Sherpa completed the task without sufficient evidence.")
            task.evidence = evidence
            task.current_step = task.summary
            await self._emit(task, {
                "type": "task_completed",
                "message": task.summary,
                **self.snapshot(task),
            })
            memory_manager.schedule(
                source_type="task",
                source_id=task.id,
                user_text=task.request or instruction,
                assistant_text=task.summary,
                tool_assisted=True,
            )
        except TaskSteeringBoundary as boundary:
            prompt = await self._directive_prompt(task, [boundary.directive])
            await self._run_with_computer(task, prompt, resume=True)
        except TaskQuestionBoundary:
            raise
        except asyncio.CancelledError:
            if task.status != "cancelled":
                task.status = "cancelled"
                task.phase = "cancelled"
                task.summary = "Sherpa stopped the task."
                await self._emit(task, {
                    "type": "task_cancelled",
                    "message": task.summary,
                    **self.snapshot(task),
                })
        except Exception as error:
            task.status = "failed"
            task.phase = "failed"
            task.summary = str(error)
            task.current_step = task.summary
            logger.exception("task.failed task=%s", task.id)
            await self._emit(task, {
                "type": "task_failed",
                "message": f"Sherpa could not finish: {error}",
                **self.snapshot(task),
            })

    def _take_directive(self, task: SherpaTask) -> dict[str, Any] | None:
        try:
            return task.directives.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def _wait_for_answer(
        self,
        task: SherpaTask,
        question_id: str,
    ) -> list[dict[str, Any]]:
        directives: list[dict[str, Any]] = []
        while True:
            directive = await task.directives.get()
            directives.append(directive)
            if (
                directive["type"] == "answer"
                and directive.get("question_id") == question_id
            ):
                return directives

    async def _directive_prompt(
        self,
        task: SherpaTask,
        directives: list[dict[str, Any]],
    ) -> str:
        while (queued := self._take_directive(task)) is not None:
            directives.append(queued)
        lines: list[str] = []
        for directive in directives:
            if directive["type"] == "answer":
                lines.append(
                    f"Answer to your question '{directive['question']}': "
                    f"{directive['answer']}"
                )
            else:
                lines.append(f"The user changed the active task: {directive['instruction']}")
        task.phase = "working"
        task.current_step = "Applying the latest direction"
        await self._emit(task, {"type": "task_steering_applied", **self.snapshot(task)})
        return "\n".join([
            *lines,
            "Continue this same task from its current state.",
            "Keep verified completed work and do not repeat it.",
            "Observe the current interface before the next action.",
        ])

    async def _emit(self, task: SherpaTask, event: dict[str, Any]) -> None:
        event["task_id"] = task.id
        await self._emit_chat(task.chat_id, event)

    async def _emit_chat(self, chat_id: str, event: dict[str, Any]) -> None:
        for queue in tuple(self._event_queues.get(chat_id, ())):
            await queue.put(dict(event))

    def _emit_nowait(self, task: SherpaTask, event: dict[str, Any]) -> None:
        event["task_id"] = task.id
        for queue in tuple(self._event_queues.get(task.chat_id, ())):
            queue.put_nowait(dict(event))

    def _record_update(
        self,
        task: SherpaTask,
        phase: str,
        progress: int,
        message: str,
        next_step: str = "",
    ) -> None:
        clean_message = " ".join(message.split()).strip() or "Working"
        clean_progress = max(task.progress, min(100, max(0, progress)))
        if task.updates and task.updates[-1]["message"] == clean_message:
            return
        task.phase = phase
        task.progress = clean_progress
        task.current_step = clean_message
        task.updates.append({
            "phase": phase,
            "progress": clean_progress,
            "message": clean_message,
            "next_step": " ".join(next_step.split()).strip(),
            "created_at": datetime.now(UTC).isoformat(),
        })


sherpa_tasks = SherpaTaskManager()


async def submit_task(instruction: str, tool_context: ToolContext) -> dict[str, Any]:
    """Ask Sherpa to admit a request, deduplicate it, and dispatch accepted work."""
    return await sherpa_tasks.submit(tool_context.session.id, instruction)


async def inspect_task(task_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """Return the current state of a delegated Sherpa task."""
    del tool_context
    task = sherpa_tasks.get(task_id)
    if not task:
        return {"status": "not_found", "task_id": task_id}
    return sherpa_tasks.snapshot(task)


async def list_active_tasks(
    tool_context: ToolContext,
) -> dict[str, object]:
    """List running Sherpa tasks for the current voice conversation."""
    tasks = [
        sherpa_tasks.snapshot(task)
        for task in sherpa_tasks.list_active_for_chat(tool_context.session.id)
    ]
    return {"status": "success", "tasks": tasks}


async def cancel_task(task_id: str, tool_context: ToolContext) -> dict[str, str]:
    """Cancel a running Sherpa task."""
    del tool_context
    cancelled = sherpa_tasks.cancel(task_id)
    return {"status": "cancelled" if cancelled else "not_running", "task_id": task_id}


async def steer_task(
    task_id: str,
    instruction: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Queue a changed instruction for a running task's next tool boundary."""
    del tool_context
    return await sherpa_tasks.steer(task_id, instruction)


async def answer_task_question(
    task_id: str,
    question_id: str,
    answer: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Answer an open worker question and resume it when the question blocks work."""
    del tool_context
    return await sherpa_tasks.answer_question(task_id, question_id, answer)


def crypto_id() -> str:
    import uuid
    return uuid.uuid4().hex


def tool_failed(response: dict | None) -> bool:
    return bool(response and (
        response.get("isError")
        or response.get("error")
        or response.get("status") == "failed"
    ))


def tool_error_message(response: dict | None) -> str:
    if not response:
        return "The tool failed without returning an error."
    error = response.get("error")
    if isinstance(error, str) and error.strip():
        return error.strip()[:1000]
    content = response.get("content")
    if isinstance(content, list):
        text = " ".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        ).strip()
        if text:
            return text[:1000]
    return "The tool reported a failure without an explanation."


def tool_result_self_verifies(name: str, args: dict[str, Any]) -> bool:
    action = str(args.get("action", "")).lower()
    return (
        name == "computer_app" and action in {"quit", "terminate"}
    ) or (
        name == "computer_window" and action == "close"
    ) or (
        name in {"browser_snapshot", "browser_find"}
    )


def is_observation_tool(name: str) -> bool:
    return name in {
        "computer_see",
        "computer_inspect_ui",
        "browser_snapshot",
        "browser_find",
    }


def overlay_target(
    args: dict[str, Any],
    elements: dict[str, tuple[float, float]],
) -> tuple[float, float] | None:
    element_id = args.get("on")
    if isinstance(element_id, str) and element_id in elements:
        return elements[element_id]
    return None


def extract_element_targets(response: Any) -> dict[str, tuple[float, float]]:
    targets: dict[str, tuple[float, float]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, str):
            for match in PEEKABOO_ELEMENT_LINE.finditer(value):
                x = float(match.group("x"))
                y = float(match.group("y"))
                width = float(match.group("width"))
                height = float(match.group("height"))
                targets[match.group("id")] = (x + width / 2, y + height / 2)
            try:
                visit(json.loads(value))
            except (json.JSONDecodeError, TypeError):
                return
            return
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        element_id = value.get("id")
        bounds = value.get("bounds")
        if isinstance(element_id, str) and isinstance(bounds, dict):
            x = bounds.get("x")
            y = bounds.get("y")
            width = bounds.get("width")
            height = bounds.get("height")
            if all(isinstance(number, (int, float)) for number in (x, y, width, height)):
                targets[element_id] = (x + width / 2, y + height / 2)
        for nested in value.values():
            visit(nested)

    visit(response)
    return targets


def extract_browser_targets(response: Any) -> dict[str, tuple[float, float]]:
    targets: dict[str, tuple[float, float]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, str):
            for line in value.splitlines():
                match = BROWSER_BOX.search(line)
                if not match:
                    continue
                x = float(match.group("x"))
                y = float(match.group("y"))
                width = float(match.group("width"))
                height = float(match.group("height"))
                targets[match.group("ref")] = (x + width / 2, y + height / 2)
            try:
                visit(json.loads(value))
            except (json.JSONDecodeError, TypeError):
                return
            return
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if isinstance(value, dict):
            for nested in value.values():
                visit(nested)

    visit(response)
    return targets


def browser_overlay_target(
    tool_name: str,
    args: dict[str, Any],
    browser_targets: dict[str, tuple[float, float]],
    elements: list[dict[str, Any]],
) -> tuple[float, float] | None:
    reference = args.get("target")
    viewport = chrome_viewport_bounds(elements)
    if isinstance(reference, str) and reference in browser_targets and viewport:
        local_x, local_y = browser_targets[reference]
        return viewport["x"] + local_x, viewport["y"] + local_y

    description = args.get("element")
    if isinstance(description, str) and description.strip():
        target = find_chrome_accessibility_target(description, elements)
        if target:
            return target

    window = chrome_window_bounds(elements)
    if tool_name == "browser_tabs" and window:
        return window["x"] + window["width"] * 0.5, window["y"] + 22
    if tool_name in {"browser_navigate", "browser_navigate_back"} and window:
        return window["x"] + window["width"] * 0.5, window["y"] + 66
    if viewport:
        return (
            viewport["x"] + viewport["width"] * 0.5,
            viewport["y"] + min(90, viewport["height"] * 0.16),
        )
    return None


async def chrome_accessibility_elements() -> list[dict[str, Any]]:
    """Read Chrome once so all overlay coordinates share macOS screen space."""
    process = await asyncio.create_subprocess_exec(
        str((Path(__file__).resolve().parents[1] / "node_modules/.bin/peekaboo")),
        "see",
        "--app",
        "Google Chrome",
        "--tree",
        "--no-screenshot",
        "--json-output",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await process.communicate()
    if process.returncode != 0:
        return []
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    elements = payload.get("data", {}).get("ui_elements", [])
    return elements if isinstance(elements, list) else []


def find_chrome_accessibility_target(
    description: str,
    elements: list[dict[str, Any]],
) -> tuple[float, float] | None:
    query = normalize_label(description)
    for element in elements:
        labels = (
            element.get("description"),
            element.get("label"),
            element.get("title"),
        )
        if not any(query in normalize_label(label) for label in labels if label):
            continue
        bounds = element.get("bounds", {})
        values = tuple(bounds.get(key) for key in ("x", "y", "width", "height"))
        if all(isinstance(value, (int, float)) for value in values):
            x, y, width, height = values
            return x + width / 2, y + height / 2
    return None


def chrome_window_bounds(
    elements: list[dict[str, Any]],
) -> dict[str, float] | None:
    for element in elements:
        if element.get("role_description") != "standard window":
            continue
        bounds = numeric_bounds(element.get("bounds"))
        if bounds:
            return bounds
    return None


def chrome_viewport_bounds(
    elements: list[dict[str, Any]],
) -> dict[str, float] | None:
    window = chrome_window_bounds(elements)
    if not window:
        return None
    candidates = []
    for element in elements:
        bounds = numeric_bounds(element.get("bounds"))
        if not bounds:
            continue
        if (
            bounds["y"] >= window["y"] + 60
            and bounds["width"] >= window["width"] * 0.8
            and bounds["height"] >= window["height"] * 0.5
        ):
            candidates.append(bounds)
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda bounds: (bounds["y"], -bounds["width"] * bounds["height"]),
    )


def numeric_bounds(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    numbers = tuple(value.get(key) for key in ("x", "y", "width", "height"))
    if not all(isinstance(number, (int, float)) for number in numbers):
        return None
    x, y, width, height = numbers
    return {
        "x": float(x),
        "y": float(y),
        "width": float(width),
        "height": float(height),
    }


def normalize_label(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def preview_target_for(
    tool_name: str,
    args: dict[str, Any],
) -> dict[str, str | int | None] | None:
    if tool_name.startswith("browser_"):
        return ComputerTarget(app="Google Chrome").snapshot()
    if not tool_name.startswith("computer_"):
        return None
    target = ComputerTarget.from_args(args)
    if not target.key and tool_name == "computer_app":
        app = next((
            args.get(key)
            for key in ("name", "to")
            if isinstance(args.get(key), str) and args.get(key)
        ), None)
        target = ComputerTarget(app=app)
    return target.snapshot() if target.key else None


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
    browser_target = next((args[key] for key in ("element", "url", "text")
                           if isinstance(args.get(key), str) and args[key]), "")
    if name == "browser_navigate":
        return f"Opening {browser_target or 'the page'}"
    if name in {"browser_snapshot", "browser_find"}:
        return f"Reading {browser_target or 'the page'}"
    if name == "browser_click":
        return f"Clicking {browser_target or 'the page control'}"
    if name in {"browser_type", "browser_fill_form"}:
        return "Typing in the page"
    if name == "browser_select_option":
        return f"Selecting {browser_target or 'an option'}"
    if name == "browser_press_key":
        return "Pressing a browser key"
    if name == "browser_tabs":
        return "Checking browser tabs"
    if name == "browser_wait_for":
        return "Waiting for the page"
    if name.startswith("browser_"):
        return name.removeprefix("browser_").replace("_", " ").capitalize()
    return name.removeprefix("computer_").replace("_", " ").capitalize()


def describe_result(name: str, failed: bool) -> str:
    action = name.removeprefix("computer_").removeprefix("browser_").replace("_", " ")
    return f"{action.capitalize()} {'failed' if failed else 'finished'}"


def merge_stream_text(current: str, incoming: str) -> str:
    """Merge ADK text deltas without repeating a cumulative final message."""
    if not incoming or current.endswith(incoming):
        return current
    if incoming.startswith(current):
        return incoming
    return current + incoming
