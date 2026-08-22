import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.agents.task_planner import TaskOperation, TaskPlan
from backend.account_context import ActiveAccount, account_context
from backend.sherpa_tasks import (
    SherpaSubmission,
    SherpaTask,
    SherpaTaskManager,
    extract_computer_target,
    is_observation_tool,
    tool_result_outcome,
    tool_result_status,
    preview_target_for,
    tool_result_dispatched_mutation,
    tool_result_self_verifies,
    build_worker_session_id,
)


class SequentialTaskTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.manager = SherpaTaskManager()

    async def asyncTearDown(self) -> None:
        await self.manager.close()

    def test_worker_session_ids_are_agent_engine_safe(self) -> None:
        session_id = build_worker_session_id(
            "15073c48-541c-4af1-8c6c-2e74e67a8017",
            "task_123",
        )
        restart_id = build_worker_session_id(
            "15073c48-541c-4af1-8c6c-2e74e67a8017",
            "task_123",
            "restart_456",
        )

        self.assertEqual(
            session_id,
            build_worker_session_id(
                "15073c48-541c-4af1-8c6c-2e74e67a8017",
                "task_123",
            ),
        )
        self.assertNotEqual(session_id, restart_id)
        self.assertLessEqual(len(session_id), 63)
        self.assertLessEqual(len(restart_id), 63)
        self.assertRegex(session_id, r"^[a-z][a-z0-9-]*[a-z0-9]$")
        self.assertRegex(restart_id, r"^[a-z][a-z0-9-]*[a-z0-9]$")

    def test_tasks_are_isolated_by_active_account(self) -> None:
        first = ActiveAccount(id="first", email="first@example.com", name="First")
        second = ActiveAccount(id="second", email="second@example.com", name="Second")
        self.manager._tasks["first-task"] = SherpaTask(
            id="first-task",
            account_id=first.id,
            chat_id="shared-chat",
            instruction="First task",
        )
        self.manager._tasks["second-task"] = SherpaTask(
            id="second-task",
            account_id=second.id,
            chat_id="shared-chat",
            instruction="Second task",
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "backend.account_context.APPLICATION_DIRECTORY",
            Path(directory),
        ):
            try:
                account_context.activate(first)
                self.assertEqual([task.id for task in self.manager.list_for_chat("shared-chat")], ["first-task"])
                account_context.activate(second)
                self.assertEqual([task.id for task in self.manager.list_for_chat("shared-chat")], ["second-task"])
            finally:
                account_context.clear()

    async def test_second_task_waits_for_first(self) -> None:
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        second_started = asyncio.Event()
        starts: list[str] = []

        async def run(task, instruction: str, handoff: str = "") -> None:
            del handoff
            starts.append(instruction)
            if instruction == "first":
                first_started.set()
                await release_first.wait()
            else:
                second_started.set()
            task.status = "completed"

        with patch.object(self.manager, "_run_worker", side_effect=run):
            first = self.manager._create_task("chat", "first", "first")
            await first_started.wait()
            second = self.manager._create_task("chat", "second", "second")

            self.assertEqual(second.phase, "queued")
            self.assertFalse(second_started.is_set())
            release_first.set()
            await first.worker
            await second.worker

        self.assertEqual(starts, ["first", "second"])

    async def test_planner_can_reuse_active_task(self) -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        async def run(task, instruction: str, handoff: str = "") -> None:
            del instruction, handoff
            started.set()
            await release.wait()
            task.status = "completed"

        with patch.object(self.manager, "_run_worker", side_effect=run):
            first = self.manager._create_task("chat", "Open Mail", "Open Mail")
            await started.wait()
            submission = SherpaSubmission(id="submission", chat_id="chat", instruction="Open Mail")
            await self.manager._apply_plan(submission, TaskPlan(
                message="Already working on that.",
                operations=[TaskOperation(
                    action="reuse",
                    task_id=first.id,
                    title="",
                    instruction="",
                    key="",
                )],
            ))
            self.assertEqual(submission.decision, "already_active")
            self.assertEqual(submission.task_id, first.id)
            self.assertEqual(len(self.manager.list_for_chat("chat")), 1)
            release.set()
            await first.worker

    async def test_cancelled_queued_task_never_runs(self) -> None:
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        starts: list[str] = []

        async def run(task, instruction: str, handoff: str = "") -> None:
            del handoff
            starts.append(instruction)
            if instruction == "first":
                first_started.set()
                await release_first.wait()
            task.status = "completed"

        with patch.object(self.manager, "_run_worker", side_effect=run):
            first = self.manager._create_task("chat", "first", "first")
            await first_started.wait()
            second = self.manager._create_task("chat", "second", "second")
            self.assertTrue(self.manager.cancel(second.id))
            release_first.set()
            await first.worker
            await asyncio.gather(second.worker, return_exceptions=True)

        self.assertEqual(starts, ["first"])

    async def test_planner_can_create_three_ordered_tasks(self) -> None:
        release = asyncio.Event()
        starts: list[str] = []

        async def run(task, instruction: str, handoff: str = "") -> None:
            del handoff
            async with self.manager._execution_lease:
                starts.append(instruction)
                if instruction == "one":
                    await release.wait()
                task.status = "completed"

        plan = TaskPlan(
            message="Queued three tasks.",
            operations=[
                TaskOperation(action="create", task_id="", title="One", instruction="one", key="one"),
                TaskOperation(action="create", task_id="", title="Two", instruction="two", key="two"),
                TaskOperation(action="create", task_id="", title="Three", instruction="three", key="three"),
            ],
        )
        submission = SherpaSubmission(id="submission", chat_id="chat", instruction="three things")

        with patch.object(self.manager, "_run_worker", side_effect=run):
            await self.manager._apply_plan(submission, plan)
            await asyncio.sleep(0)
            tasks = self.manager.list_for_chat("chat")
            self.assertEqual([task.instruction for task in tasks], ["One", "Two", "Three"])
            self.assertEqual([task.phase for task in tasks[1:]], ["queued", "queued"])
            self.assertEqual(starts, ["one"])
            release.set()
            await asyncio.gather(*(task.worker for task in tasks))

        self.assertEqual(starts, ["one", "two", "three"])

    async def test_planner_schema_does_not_cap_operations_or_task_metadata(self) -> None:
        operations = [
            TaskOperation(
                action="create",
                task_id="",
                title=f"Task {index}",
                instruction=f"instruction {index}",
                key=f"task-{index}",
                skill_ids=["workspace-spreadsheets"] * 5,
                required_inputs=[f"input-{item}" for item in range(10)],
                expected_outputs=[f"output-{item}" for item in range(10)],
            )
            for index in range(7)
        ]

        plan = TaskPlan(message="Queued.", operations=operations)

        self.assertEqual(len(plan.operations), 7)
        self.assertEqual(len(plan.operations[0].required_inputs), 10)

    async def test_queued_task_update_replaces_plan_before_execution(self) -> None:
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        starts: list[str] = []

        async def run(task, instruction: str, handoff: str = "", **kwargs) -> None:
            del handoff, kwargs
            starts.append(instruction)
            if instruction == "first":
                first_started.set()
                await release_first.wait()
            task.status = "completed"

        with patch.object(self.manager, "_run_with_computer", side_effect=run):
            first = self.manager._create_task("chat", "First", "first")
            await first_started.wait()
            second = self.manager._create_task("chat", "Old title", "old instruction")
            result = await self.manager.update(
                second.id,
                "new instruction",
                title="New title",
                skill_ids=["workspace-spreadsheets"],
            )
            self.assertEqual(result["status"], "updated")
            self.assertEqual(second.instruction, "New title")
            self.assertEqual(second.skill_ids, ["workspace-spreadsheets"])
            release_first.set()
            await asyncio.gather(first.worker, second.worker)

        self.assertEqual(starts, ["first", "new instruction"])

    async def test_queued_task_cannot_be_steered(self) -> None:
        task = SherpaTask(id="task", chat_id="chat", instruction="Queued")
        self.manager._tasks[task.id] = task

        result = await self.manager.steer(task.id, "change")

        self.assertEqual(result["status"], "not_working")
        self.assertEqual(result["task_status"], "queued")
        self.assertIn("update_task", result["guidance"])

    async def test_running_task_cannot_be_updated(self) -> None:
        task = SherpaTask(
            id="task",
            chat_id="chat",
            instruction="Running",
            status="running",
        )
        self.manager._tasks[task.id] = task

        result = await self.manager.update(task.id, "change")

        self.assertEqual(result["status"], "not_queued")
        self.assertEqual(result["task_status"], "running")
        self.assertIn("steer_task", result["guidance"])

    async def test_running_task_steer_becomes_next_model_instruction(self) -> None:
        task = SherpaTask(
            id="task",
            chat_id="chat",
            instruction="Find Dev's video",
            status="running",
        )
        self.manager._tasks[task.id] = task

        result = await self.manager.steer(task.id, "Find Ben's video instead")
        directive = self.manager._take_directive(task)
        prompt = await self.manager._directive_prompt(task, [directive], restart=True)

        self.assertEqual(result["status"], "queued")
        self.assertIn("The user changed the active task: Find Ben's video instead", prompt)
        self.assertIn("Restart the task using this latest direction", prompt)
        self.assertIn("Re-observe the current external state", prompt)
        self.assertEqual(task.current_step, "Applying the latest direction")

    async def test_dependency_handoff_includes_structured_outputs(self) -> None:
        dependency = SherpaTask(
            id="dependency",
            chat_id="chat",
            instruction="Create result",
            outputs=[{
                "name": "spreadsheet",
                "type": "google_sheet",
                "value": "https://docs.google.com/spreadsheets/d/example",
                "verification": "Read Sheet1 after writing.",
            }],
        )
        task = SherpaTask(
            id="consumer",
            chat_id="chat",
            instruction="Use result",
            required_inputs=["spreadsheet"],
        )

        handoff = self.manager._dependency_handoff(task, [dependency])

        self.assertIn('"type": "google_sheet"', handoff)
        self.assertIn('"value": "https://docs.google.com/spreadsheets/d/example"', handoff)

    async def test_structured_outputs_are_required_only_for_active_dependents(self) -> None:
        producer = SherpaTask(
            id="producer",
            chat_id="chat",
            instruction="Produce result",
            expected_outputs=["result"],
        )
        self.manager._tasks[producer.id] = producer
        self.assertFalse(self.manager.requires_handoff(producer))

        consumer = SherpaTask(
            id="consumer",
            chat_id="chat",
            instruction="Consume result",
            depends_on=[producer.id],
        )
        self.manager._tasks[consumer.id] = consumer
        self.assertTrue(self.manager.requires_handoff(producer))

        consumer.status = "completed"
        self.assertFalse(self.manager.requires_handoff(producer))

    async def test_planner_attaches_multiple_skills_to_one_task(self) -> None:
        plan = TaskPlan(
            message="Queued the workflow.",
            operations=[TaskOperation(
                action="create",
                task_id="",
                title="Share prize details",
                instruction="Find the email, create a Doc, then send it on WhatsApp.",
                skill_ids=["workspace-email", "workspace-documents", "native-whatsapp"],
                key="share-prize",
            )],
        )
        submission = SherpaSubmission(id="submission", chat_id="chat", instruction="share details")

        async def run(task, instruction: str, handoff: str = "") -> None:
            del instruction, handoff
            task.status = "completed"

        with patch.object(self.manager, "_run_worker", side_effect=run):
            await self.manager._apply_plan(submission, plan)
            task = self.manager.get(submission.task_id or "")
            self.assertIsNotNone(task)
            self.assertEqual(task.skill_ids, plan.operations[0].skill_ids)
            await task.worker

    async def test_planner_rejects_unknown_skills(self) -> None:
        plan = TaskPlan(
            message="Queued.",
            operations=[TaskOperation(
                action="create",
                task_id="",
                title="Unknown",
                instruction="Do something.",
                skill_ids=["not-a-real-skill"],
                key="unknown",
            )],
        )
        with self.assertRaisesRegex(RuntimeError, "unknown skills"):
            self.manager._validate_plan("chat", plan)

    async def test_workspace_reads_count_as_verification(self) -> None:
        self.assertTrue(is_observation_tool("workspace_sheets_read_range"))
        self.assertTrue(is_observation_tool("workspace_docs_read_doc"))
        self.assertFalse(is_observation_tool("workspace_sheets_update_range"))

    async def test_application_and_window_lists_are_observations(self) -> None:
        self.assertTrue(is_observation_tool("computer_app", {"action": "list"}))
        self.assertTrue(is_observation_tool("computer_window", {"action": "list"}))
        self.assertFalse(is_observation_tool("computer_app", {"action": "quit"}))

    async def test_read_only_browser_evaluate_counts_as_observation(self) -> None:
        self.assertTrue(is_observation_tool("browser_evaluate"))
        self.assertFalse(tool_result_self_verifies("browser_evaluate", {}))

    async def test_confirmed_computer_receipt_self_verifies(self) -> None:
        response = {
            "metadata": {
                "effect": "confirmed",
                "mutation_dispatched": True,
                "requires_fresh_observation": False,
            },
        }

        self.assertTrue(tool_result_self_verifies(
            "computer_click",
            {"on": "B1"},
            response,
        ))

    async def test_unverified_computer_receipt_requires_observation(self) -> None:
        response = {
            "metadata": {
                "effect": "unverifiable",
                "mutation_dispatched": True,
                "requires_fresh_observation": True,
            },
        }

        self.assertFalse(tool_result_self_verifies(
            "computer_click",
            {"on": "B1"},
            response,
        ))
        self.assertTrue(tool_result_dispatched_mutation(response))

    async def test_local_artifact_inspection_counts_as_verification(self) -> None:
        self.assertTrue(is_observation_tool("inspect_local_artifacts"))
        self.assertTrue(tool_result_self_verifies("inspect_local_artifacts", {}))

    async def test_compound_file_dialog_self_verifies(self) -> None:
        self.assertTrue(tool_result_self_verifies(
            "computer_dialog",
            {"action": "file"},
        ))

    async def test_computer_result_exposes_transitioned_window(self) -> None:
        result = extract_computer_target({
            "data": {
                "resultingWindow": {
                    "application": "WhatsApp",
                    "pid": 42,
                    "windowId": 91,
                    "title": "Open",
                },
            },
        })

        self.assertEqual(result, {
            "app": "WhatsApp",
            "pid": 42,
            "window_id": 91,
            "window_title": "Open",
        })

    async def test_computer_result_joins_window_inventory_owner(self) -> None:
        result = extract_computer_target({
            "data": {
                "windows": [{"window_id": 2153, "window_title": "WhatsApp"}],
                "target_application_info": {
                    "app_name": "WhatsApp",
                    "pid": 6773,
                },
            },
        })

        self.assertEqual(result, {
            "app": "WhatsApp",
            "pid": 6773,
            "window_id": 2153,
            "window_title": "WhatsApp",
        })

    async def test_structured_tool_outcomes_are_preserved(self) -> None:
        response = {
            "status": "download_started",
            "outcome": "Chrome accepted the download request.",
        }
        self.assertEqual(tool_result_status(response), "download_started")
        self.assertEqual(
            tool_result_outcome(response),
            "Chrome accepted the download request.",
        )
        self.assertEqual(tool_result_status(response, failed=True), "failed")

    async def test_window_preview_requires_verified_ownership(self) -> None:
        self.assertIsNone(preview_target_for("computer_see", {"window_id": 1664}))
        self.assertEqual(
            preview_target_for(
                "computer_see",
                {"window_id": 1664},
                {"app": "Finder", "pid": None, "window_id": None, "window_title": None},
            ),
            {"app": "Finder", "pid": None, "window_id": 1664, "window_title": None},
        )


if __name__ == "__main__":
    unittest.main()
