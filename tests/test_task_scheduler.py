import asyncio
import types
import unittest

from backend.sherpa_tasks import SherpaTask, SherpaTaskManager
from backend.task_graph import WorkerAssignment


class TaskSchedulerTests(unittest.IsolatedAsyncioTestCase):
    def manager(self) -> SherpaTaskManager:
        manager = SherpaTaskManager.__new__(SherpaTaskManager)
        manager._tasks = {}
        manager._event_queues = {}
        return manager

    def assignment(
        self,
        key: str,
        *,
        depends_on: list[str] | None = None,
    ) -> WorkerAssignment:
        return WorkerAssignment(
            key=key,
            title=key.title(),
            instruction=f"Complete {key}",
            tools=["computer"],
            depends_on=depends_on or [],
        )

    def children(
        self,
        assignments: list[WorkerAssignment],
    ) -> tuple[SherpaTaskManager, dict[str, SherpaTask]]:
        manager = self.manager()
        parent = SherpaTask(id="parent", chat_id="chat", instruction="Parent")
        children = {
            assignment.key: manager._create_worker(parent, assignment)
            for assignment in assignments
        }
        return manager, children

    async def test_starts_independent_assignments_concurrently(self) -> None:
        assignments = [self.assignment("first"), self.assignment("second")]
        manager, children = self.children(assignments)
        started: set[str] = set()
        both_started = asyncio.Event()
        release = asyncio.Event()

        async def run_worker(_manager, task: SherpaTask, instruction: str) -> None:
            del instruction
            started.add(task.instruction.casefold())
            if len(started) == 2:
                both_started.set()
            await release.wait()
            task.status = "completed"
            task.summary = f"Finished {task.instruction}"

        manager._run_worker = types.MethodType(run_worker, manager)
        run = asyncio.create_task(manager._run_assignment_graph(
            {assignment.key: assignment for assignment in assignments},
            children,
        ))
        await asyncio.wait_for(both_started.wait(), timeout=1)
        self.assertEqual(started, {"first", "second"})
        release.set()
        await run

    async def test_hands_completed_result_to_dependent_assignment(self) -> None:
        assignments = [
            self.assignment("first"),
            self.assignment("second", depends_on=["first"]),
        ]
        manager, children = self.children(assignments)
        calls: list[tuple[str, str]] = []

        async def run_worker(_manager, task: SherpaTask, instruction: str) -> None:
            calls.append((task.instruction, instruction))
            task.status = "completed"
            task.summary = f"Verified result from {task.instruction}"
            task.evidence = f"Evidence from {task.instruction}"

        manager._run_worker = types.MethodType(run_worker, manager)
        await manager._run_assignment_graph(
            {assignment.key: assignment for assignment in assignments},
            children,
        )

        self.assertEqual([title for title, _ in calls], ["First", "Second"])
        self.assertIn("Verified result from First", calls[1][1])
        self.assertIn("Evidence from First", calls[1][1])
        self.assertIn("Do not repeat their work", calls[1][1])


if __name__ == "__main__":
    unittest.main()
