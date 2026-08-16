import unittest

from backend.main import final_transcript_event
from backend.tools.voice_tools import VOICE_TOOLS, task_ledger_response
from backend.voice_notifications import task_state_notification


class VoiceNotificationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
