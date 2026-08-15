import asyncio
import unittest
from unittest.mock import patch

from backend.agents.task_planner import TaskOperation, TaskPlan
from backend.sherpa_tasks import SherpaSubmission, SherpaTaskManager, is_observation_tool


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

        async def run(task, instruction: str) -> None:
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

        async def run(task, instruction: str) -> None:
            started.set()
            await release.wait()
            task.status = "completed"

        with patch.object(self.manager, "_run_worker", side_effect=run):
            first = self.manager._create_task("chat", "Open Mail", "Open Mail")
            await started.wait()
            submission = SherpaSubmission(id="submission", chat_id="chat", instruction="Open Mail")
            await self.manager._apply_plan(submission, TaskPlan(
                message="Already working on that.",
                operations=[TaskOperation(action="reuse", task_id=first.id)],
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

        async def run(task, instruction: str) -> None:
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

        async def run(task, instruction: str) -> None:
            starts.append(instruction)
            if instruction == "one":
                await release.wait()
            task.status = "completed"

        plan = TaskPlan(
            message="Queued three tasks.",
            operations=[
                TaskOperation(action="create", title="One", instruction="one"),
                TaskOperation(action="create", title="Two", instruction="two"),
                TaskOperation(action="create", title="Three", instruction="three"),
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

    async def test_planner_attaches_multiple_skills_to_one_task(self) -> None:
        plan = TaskPlan(
            message="Queued the workflow.",
            operations=[TaskOperation(
                action="create",
                title="Share prize details",
                instruction="Find the email, create a Doc, then send it on WhatsApp.",
                skill_ids=["workspace-email", "workspace-documents", "native-whatsapp"],
            )],
        )
        submission = SherpaSubmission(id="submission", chat_id="chat", instruction="share details")

        async def run(task, instruction: str) -> None:
            del instruction
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
                title="Unknown",
                instruction="Do something.",
                skill_ids=["not-a-real-skill"],
            )],
        )
        with self.assertRaisesRegex(RuntimeError, "unknown skills"):
            self.manager._validate_plan("chat", plan)

    async def test_workspace_reads_count_as_verification(self) -> None:
        self.assertTrue(is_observation_tool("workspace_sheets_read_range"))
        self.assertTrue(is_observation_tool("workspace_docs_read_doc"))
        self.assertFalse(is_observation_tool("workspace_sheets_update_range"))


if __name__ == "__main__":
    unittest.main()
