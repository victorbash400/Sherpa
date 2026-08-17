import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.skill_store import SkillStore, skill_store


class SkillStoreTests(unittest.TestCase):
    def test_default_skills_load(self) -> None:
        skills = {skill.id: skill for skill in skill_store.all()}

        self.assertIn("native-whatsapp", skills)
        self.assertIn("workspace-email", skills)
        self.assertIn("workspace-documents", skills)
        self.assertIn("workspace-tasks", skills)
        self.assertIn("workspace-forms", skills)
        self.assertIn("workspace-meet", skills)

    def test_selected_skills_are_combined_without_keyword_matching(self) -> None:
        context = skill_store.context_for(["workspace-email", "native-whatsapp"])

        self.assertIn("Never navigate to WhatsApp Web", context)
        self.assertIn("workspace_gmail_search_threads", context)

    def test_unknown_skills_are_not_loaded(self) -> None:
        self.assertEqual(skill_store.context_for(["made-up-skill"]), "")

    def test_chrome_skill_routes_repetitive_dom_edits_to_page_code(self) -> None:
        context = skill_store.context_for(["chrome-web-workflows"])

        self.assertIn("browser_evaluate", context)
        self.assertIn("Do not alternate full snapshots", context)

    def test_native_file_removal_is_grounded_and_recoverable(self) -> None:
        context = skill_store.context_for(["native-macos-apps"])

        self.assertIn("action=launch", context)
        self.assertIn("Never select a file for removal with an ungrounded coordinate-only click", context)
        self.assertIn("Move the selected file to Trash", context)
        self.assertIn("verify that the exact filename is absent", context)

    def test_native_dialog_transition_uses_compound_file_action(self) -> None:
        context = skill_store.context_for(["native-macos-apps", "native-whatsapp"])

        self.assertIn("action=file", context)
        self.assertIn("exact absolute `path`", context)
        self.assertIn("Do not inspect or click through the file picker manually", context)

    def test_skill_instructions_can_be_overridden(self) -> None:
        with TemporaryDirectory() as directory:
            store = SkillStore(Path(directory) / "skills.json")
            updated = store.update("workspace-email", "Use the narrowest Gmail query.")

            self.assertEqual(updated.instructions, "Use the narrowest Gmail query.")
            self.assertEqual(
                next(skill for skill in store.all() if skill.id == "workspace-email").instructions,
                "Use the narrowest Gmail query.",
            )


if __name__ == "__main__":
    unittest.main()
