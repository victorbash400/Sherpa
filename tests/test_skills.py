import unittest

from backend.skill_store import skill_store


class SkillStoreTests(unittest.TestCase):
    def test_default_skills_load(self) -> None:
        skills = {skill.id: skill for skill in skill_store.all()}

        self.assertIn("native-whatsapp", skills)
        self.assertIn("google-workspace", skills)
        self.assertEqual(skills["native-whatsapp"].snapshot()["name"], "Native WhatsApp")

    def test_whatsapp_request_selects_native_app_skill(self) -> None:
        context = skill_store.context_for("Send this to Alice on WhatsApp")

        self.assertIn("Never navigate to WhatsApp Web", context)
        self.assertNotIn("workspace_*", context)

    def test_docs_request_selects_workspace_api_skill(self) -> None:
        context = skill_store.context_for("Create a Google Doc with these notes")

        self.assertIn("workspace_*", context)
        self.assertNotIn("WhatsApp Web", context)


if __name__ == "__main__":
    unittest.main()
