import unittest

from backend.voice_notifications import task_state_notification


class VoiceNotificationTests(unittest.TestCase):
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
