import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.account_context import ActiveAccount, account_context
from backend.google_auth import GoogleAuthManager
from backend.memory_store import MemoryStore
from backend.permission_store import PermissionStore
from backend.skill_store import SkillStore
from backend.local_tool_dispatcher import LocalToolDispatcher


class AccountIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path_patch = patch(
            "backend.account_context.APPLICATION_DIRECTORY",
            Path(self.directory.name),
        )
        self.path_patch.start()
        self.first = ActiveAccount(id="first", email="first@example.com", name="First")
        self.second = ActiveAccount(id="second", email="second@example.com", name="Second")

    def tearDown(self) -> None:
        account_context.clear()
        self.path_patch.stop()
        self.directory.cleanup()

    def test_memory_is_isolated(self) -> None:
        store = MemoryStore()
        account_context.activate(self.first)
        store.remember(category="preference", content="First memory", source_type="chat", source_id="one", editable=True)

        account_context.activate(self.second)
        self.assertEqual(store.snapshot()["memories"], [])
        store.remember(category="preference", content="Second memory", source_type="chat", source_id="two", editable=True)

        account_context.activate(self.first)
        self.assertEqual([item["content"] for item in store.snapshot()["memories"]], ["First memory"])

    def test_skill_overrides_and_permissions_use_profile_directories(self) -> None:
        skills = SkillStore()
        permissions = PermissionStore()
        account_context.activate(self.first)
        skill = skills.all()[0]
        skills.update(skill.id, "First account instructions")
        permissions.set("workspace.gmail", False)

        account_context.activate(self.second)
        self.assertNotEqual(skills.all()[0].instructions, "First account instructions")
        permissions.activate_account()
        permissions.set("workspace.gmail", False)

        self.assertTrue((Path(self.directory.name) / "profiles/first/skills.json").is_file())
        self.assertTrue((Path(self.directory.name) / "profiles/first/permissions.json").is_file())
        self.assertTrue((Path(self.directory.name) / "profiles/second/permissions.json").is_file())

    def test_google_keychain_service_is_namespaced(self) -> None:
        account_context.activate(self.first)
        first_service = GoogleAuthManager._keychain_service("workspace")
        account_context.activate(self.second)
        second_service = GoogleAuthManager._keychain_service("workspace")

        self.assertNotEqual(first_service, second_service)
        self.assertIn(self.first.id, first_service)
        self.assertIn(self.second.id, second_service)


class LocalToolAccountIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_tool_request_for_another_account(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "backend.account_context.APPLICATION_DIRECTORY",
            Path(directory),
        ):
            account_context.activate(ActiveAccount(id="current", email="current@example.com", name="Current"))
            try:
                result = await LocalToolDispatcher().run(
                    name="save_memory",
                    args={},
                    state={"account_id": "other"},
                    function_call_id="call",
                    session_id="session",
                )
            finally:
                account_context.clear()

        self.assertEqual(result["status"], "failed")
        self.assertIn("signed-in Sherpa account", result["error"])


if __name__ == "__main__":
    unittest.main()
