import unittest

from google.genai import types

from backend.main import final_transcript_event
from backend.sherpa_tasks import SherpaTask, sherpa_tasks
from backend.tools.voice_tools import (
    VOICE_TOOLS,
    handle_voice_tool_call,
    task_ledger_response,
)
from backend.voice_notifications import task_state_notification


class VoiceNotificationTests(unittest.IsolatedAsyncioTestCase):
    def test_turn_completion_finalizes_pending_user_transcript(self) -> None:
        event = final_transcript_event(
            "voice-user-3",
            "user",
            3,
            "Show my exact words",
        )

        self.assertEqual(event, {
            "type": "transcript_update",
            "id": "voice-user-3",
            "role": "user",
            "sequence": 3,
            "text": "Show my exact words",
            "final": True,
        })

    def test_voice_exposes_distinct_update_and_steer_tools(self) -> None:
        names = {
            declaration.name
            for tool in VOICE_TOOLS
            for declaration in tool.function_declarations or []
        }

        self.assertIn("update_task", names)
        self.assertIn("steer_task", names)
        self.assertIn("remember_for_task", names)
        self.assertIn("capture_photo", names)

    async def test_capture_photo_returns_saved_path(self) -> None:
        responses = []

        async def respond(call_id: str, name: str, response: dict) -> None:
            responses.append((call_id, name, response))

        async def capture(call_id: str) -> dict:
            self.assertEqual(call_id, "capture-1")
            return {"status": "captured", "path": "/Pictures/Sherpa Captures/photo.jpg", "mime_type": "image/jpeg"}

        await handle_voice_tool_call(
            types.FunctionCall(id="capture-1", name="capture_photo", args={}),
            "voice-chat",
            respond,
            capture,
        )

        self.assertEqual(responses[0][2]["status"], "captured")
        self.assertEqual(responses[0][2]["path"], "/Pictures/Sherpa Captures/photo.jpg")

    def test_completed_event_keeps_downstream_tasks_grounded(self) -> None:
        prompt = task_state_notification(
            [{
                "task_id": "research",
                "instruction": "Research and create Doc",
                "status": "completed",
                "message": "The Doc was created.",
            }],
            [
                {
                    "instruction": "Research and create Doc",
                    "status": "completed",
                    "current_step": "The Doc was created.",
                },
                {
                    "instruction": "Create Canva PDF",
                    "status": "running",
                    "current_step": "Editing the Canva design",
                },
                {
                    "instruction": "Send email",
                    "status": "queued",
                    "current_step": "Waiting for prerequisite tasks",
                },
            ],
        )

        self.assertIn("Create Canva PDF [running]", prompt)
        self.assertIn("Send email [queued]", prompt)
        self.assertIn("never infer downstream completion", prompt)

    def test_completed_event_includes_verified_result_details(self) -> None:
        prompt = task_state_notification(
            [{
                "task_id": "calendar",
                "instruction": "Check calendar",
                "status": "completed",
                "message": "Calendar checked.",
                "summary": "Found two events.",
                "evidence": "Calendar API returned both events.",
                "outputs": [{
                    "name": "event",
                    "type": "calendar_event",
                    "value": "Planning at 10:00",
                    "verification": "Returned by Calendar API",
                }],
            }],
            [],
        )

        self.assertIn("VERIFIED RESULT", prompt)
        self.assertIn("Planning at 10:00", prompt)
        self.assertIn("Calendar API returned both events", prompt)

    def test_task_ledger_spoken_summary_contains_verified_results(self) -> None:
        response = task_ledger_response([{
            "instruction": "List recent Docs",
            "status": "completed",
            "current_step": "Done",
            "summary": "Found the recent documents.",
            "evidence": "Drive API response was ordered by modified time.",
            "outputs": [{"name": "document", "value": "Real document"}],
        }], [])

        self.assertIn("Real document", response["spoken_summary"])
        self.assertIn("Drive API response", response["spoken_summary"])


class VoiceTaskSteeringTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.task_ids = ["voice-running", "voice-queued"]
        sherpa_tasks._tasks[self.task_ids[0]] = SherpaTask(
            id=self.task_ids[0],
            chat_id="voice-chat",
            instruction="Find Dev's video",
            status="running",
            current_step="Searching YouTube",
        )
        sherpa_tasks._tasks[self.task_ids[1]] = SherpaTask(
            id=self.task_ids[1],
            chat_id="voice-chat",
            instruction="Send the summary",
            status="queued",
            current_step="Waiting for earlier work",
        )
        self.responses: list[dict] = []

    async def asyncTearDown(self) -> None:
        for task_id in self.task_ids:
            sherpa_tasks._tasks.pop(task_id, None)

    async def respond(self, call_id: str, name: str, response: dict) -> None:
        del call_id, name
        self.responses.append(response)

    async def call(self, name: str, task_id: str, instruction: str) -> dict:
        await handle_voice_tool_call(
            types.FunctionCall(
                id=f"call-{len(self.responses)}",
                name=name,
                args={"task_id": task_id, "instruction": instruction},
            ),
            "voice-chat",
            self.respond,
        )
        return self.responses[-1]

    async def test_wrong_id_returns_all_active_choices_for_retry(self) -> None:
        response = await self.call("steer_task", "missing", "Use Ben instead")

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error"]["code"], "task_not_found")
        self.assertEqual(
            {choice["task_id"] for choice in response["task_choices"]},
            set(self.task_ids),
        )
        self.assertEqual(response["retry"]["tool"], "task_choices.change_with")

    async def test_wrong_change_tool_points_to_correct_tool(self) -> None:
        response = await self.call("update_task", self.task_ids[0], "Use Ben instead")

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error"]["code"], "wrong_task_state")
        self.assertEqual(response["retry"]["tool"], "steer_task")

    async def test_correct_steer_queues_directive(self) -> None:
        response = await self.call("steer_task", self.task_ids[0], "Use Ben instead")
        directive = sherpa_tasks._tasks[self.task_ids[0]].directives.get_nowait()

        self.assertEqual(response["status"], "queued")
        self.assertEqual(directive["instruction"], "Use Ben instead")

    async def test_remember_for_task_queues_distinct_memory_directive(self) -> None:
        response = await self.call(
            "remember_for_task",
            self.task_ids[0],
            "Remember that Dev means Marques Brownlee in this workflow",
        )
        directive = sherpa_tasks._tasks[self.task_ids[0]].directives.get_nowait()

        self.assertEqual(response["status"], "queued")
        self.assertEqual(directive["type"], "remember")
        self.assertIn("Marques Brownlee", directive["instruction"])

    async def test_remember_for_task_rejects_queued_worker(self) -> None:
        response = await self.call(
            "remember_for_task",
            self.task_ids[1],
            "Remember the workflow",
        )

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error"]["code"], "wrong_task_state")


if __name__ == "__main__":
    unittest.main()
