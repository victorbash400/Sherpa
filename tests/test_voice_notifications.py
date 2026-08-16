import unittest

from backend.tools.voice_tools import VOICE_TOOLS
from backend.voice_notifications import task_state_notification


class VoiceNotificationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
