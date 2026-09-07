from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys

SCRIPT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT))
PERSONAL_SCRIPT = Path(__file__).resolve().parents[2] / "zentao-personal" / "scripts"
sys.path.insert(0, str(PERSONAL_SCRIPT))

from project_config import project_set  # noqa: E402
from team_config import TeamStore  # noqa: E402
from zentao_testing import build_parser  # noqa: E402
from testing_team import (  # noqa: E402
    TestingTeamError,
    effective_testing_team,
    import_personal_team,
    remove_project_team,
    replace_global_team,
    replace_project_team,
    view_testing_team,
)


class FakeClient:
    account = "tester"
    connection_identity = {"base_url": "http://localhost:8080/zentao", "account": "tester"}

    def __init__(self):
        self.complete = True
        self.users = [
            {"id": 1, "account": "tester", "realname": "测试员"},
            {"id": 2, "account": "alice", "realname": "张三"},
            {"id": 3, "account": "bob", "realname": "李四"},
            {"id": 4, "account": "carol", "realname": "王五"},
        ]
        self.projects = [
            {"id": 12, "name": "商城", "products": [3]},
            {"id": 13, "name": "官网", "products": [4]},
        ]
        self.products = [
            {"id": 3, "name": "商城产品", "projects": [12]},
            {"id": 4, "name": "官网产品", "projects": [13]},
        ]

    def list_all(self, resource, *, scope=None, scope_id=None, browse=None, per_page=1000,
                 preserve_partial=False):
        rows = {"user": self.users, "project": self.projects, "product": self.products}[resource]
        return SimpleNamespace(items=list(rows), complete=self.complete, partial_failures=[] if self.complete else [{"code": "PAGE_READ_FAILED"}])


class TestingTeamTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.home = self.root / "home"
        self.home.mkdir()
        self.home_patch = patch.dict(os.environ, {"HOME": str(self.home)})
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.client = FakeClient()

    def configure_projects(self):
        project_set(self.client, alias="mall", project="12", product="3", default_build="trunk", root=self.root)
        project_set(self.client, alias="site", project="13", product="4", default_build="trunk", root=self.root)

    def test_testing_team_is_independent_from_personal_team(self):
        personal = TeamStore(self.client.connection_identity)
        personal.update("replace", ["alice"])

        saved = replace_global_team(self.client, ["bob"], root=self.root)

        self.assertEqual(["alice"], personal.read())
        self.assertEqual("testing", saved["team_domain"])
        self.assertEqual(["bob"], saved["configured_accounts"])
        self.assertEqual(["bob"], view_testing_team(self.client, root=self.root)["configured_accounts"])
        self.assertEqual(["tester", "bob"], effective_testing_team(self.client, root=self.root)["effective_accounts"])
        self.assertNotEqual(personal.path, next((self.root / "testing-teams").glob("*.json")).resolve())

    def test_project_override_replaces_global_only_for_that_project(self):
        self.configure_projects()
        replace_global_team(self.client, ["alice"], root=self.root)

        mall = replace_project_team(self.client, "mall", ["bob"], root=self.root)
        self.assertEqual("project_override", mall["source"])
        self.assertEqual(["bob"], mall["configured_accounts"])
        self.assertEqual("global_default", view_testing_team(self.client, root=self.root)["source"])
        self.assertEqual(["alice"], view_testing_team(self.client, root=self.root)["configured_accounts"])
        self.assertEqual(["tester", "bob"], effective_testing_team(self.client, project_alias="mall", root=self.root)["effective_accounts"])
        self.assertEqual(["tester", "alice"], effective_testing_team(self.client, project_alias="site", root=self.root)["effective_accounts"])

        replace_global_team(self.client, ["carol"], root=self.root)
        self.assertEqual(["bob"], effective_testing_team(self.client, project_alias="mall", root=self.root)["configured_accounts"])
        self.assertEqual(["carol"], effective_testing_team(self.client, project_alias="site", root=self.root)["configured_accounts"])

    def test_personal_import_is_explicit_and_does_not_create_sync(self):
        personal = TeamStore(self.client.connection_identity)
        personal.update("replace", ["alice"])
        self.assertEqual(["tester"], effective_testing_team(self.client, root=self.root)["effective_accounts"])

        imported = import_personal_team(self.client, root=self.root)

        self.assertEqual("explicit_personal_import", imported["source"])
        self.assertEqual(["alice"], imported["configured_accounts"])
        personal.update("replace", ["bob"])
        self.assertEqual(["alice"], view_testing_team(self.client, root=self.root)["configured_accounts"])

    def test_incomplete_user_directory_does_not_overwrite_either_domain(self):
        personal = TeamStore(self.client.connection_identity)
        personal.update("replace", ["alice"])
        replace_global_team(self.client, ["bob"], root=self.root)
        self.client.complete = False

        with self.assertRaises(TestingTeamError) as raised:
            replace_global_team(self.client, ["carol"], root=self.root)

        self.assertEqual("TESTING_TEAM_DIRECTORY_INCOMPLETE", raised.exception.code)
        self.assertEqual(["alice"], personal.read())
        self.assertEqual(["bob"], view_testing_team(self.client, root=self.root)["configured_accounts"])

    def test_ambiguous_member_and_corrupt_config_fail_closed(self):
        replace_global_team(self.client, ["alice"], root=self.root)
        path = next((self.root / "testing-teams").glob("*.json"))
        before = path.read_bytes()
        self.client.users.append({"id": 5, "account": "alice2", "realname": "张三"})
        with self.assertRaises(TestingTeamError) as raised:
            replace_global_team(self.client, ["张三"], root=self.root)
        self.assertEqual("TESTING_TEAM_USER_AMBIGUOUS", raised.exception.code)
        self.assertEqual(before, path.read_bytes())
        path.write_text("not json")
        with self.assertRaises(TestingTeamError) as raised:
            view_testing_team(self.client, root=self.root)
        self.assertEqual("TESTING_TEAM_CONFIG_INVALID", raised.exception.code)

    def test_identity_and_empty_project_override_are_distinct(self):
        self.configure_projects()
        replace_global_team(self.client, ["alice"], root=self.root)
        replace_project_team(self.client, "mall", [], root=self.root)
        empty_override = effective_testing_team(self.client, project_alias="mall", root=self.root)
        self.assertEqual("project_override", empty_override["source"])
        self.assertEqual(["tester"], empty_override["effective_accounts"])

        other_client = FakeClient()
        other_client.account = "alice"
        other_client.connection_identity = {"base_url": "http://localhost:8080/zentao", "account": "alice"}
        self.assertEqual([], view_testing_team(other_client, root=self.root)["configured_accounts"])

    def test_project_override_requires_a_saved_testing_project(self):
        with self.assertRaises(TestingTeamError) as raised:
            replace_project_team(self.client, "missing", ["bob"], root=self.root)
        self.assertEqual("TESTING_PROJECT_NOT_FOUND", raised.exception.code)
        self.assertFalse((self.root / "testing-teams").exists())

        self.configure_projects()
        result = remove_project_team(self.client, "mall", ["bob"], root=self.root)
        self.assertEqual("global_default", result["source"])
        self.assertFalse((self.root / "testing-teams").exists())

    def test_cli_exposes_testing_team_domain_separately(self):
        self.assertEqual("team-replace", build_parser().parse_args(["team-replace", "--member", "bob"]).action)
        self.assertEqual("project-team-replace", build_parser().parse_args([
            "project-team-replace", "--project-alias", "mall", "--clear"
        ]).action)
        self.assertEqual("module-set", build_parser().parse_args([
            "module-set", "--project-alias", "mall", "--alias", "payment", "--module", "45",
            "--frontend", "alice", "--backend", "bob"
        ]).action)
        self.assertNotIn("team", build_parser()._subparsers._group_actions[0].choices)


if __name__ == "__main__":
    unittest.main()
