import asyncio
import unittest
from unittest.mock import patch

from backend.agents.task_planner import TaskOperation, TaskPlan
from backend.sherpa_tasks import (
    SherpaSubmission,
    SherpaTask,
    SherpaTaskManager,
    is_observation_tool,
    preview_target_for,
    tool_result_self_verifies,
)


class SequentialTaskTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.manager = SherpaTaskManager()

    async def asyncTearDown(self) -> None:
        await self.manager.close()

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

    async def test_browser_evaluate_requires_visual_verification(self) -> None:
        self.assertFalse(is_observation_tool("browser_evaluate"))
        self.assertFalse(tool_result_self_verifies("browser_evaluate", {}))

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
