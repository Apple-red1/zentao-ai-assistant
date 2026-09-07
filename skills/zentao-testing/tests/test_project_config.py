from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import sys

SCRIPT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT))
from project_config import (TestingConfigError, context_use, context_view, module_remove, module_set,
                            project_list, project_remove, project_set)


class FakeClient:
    account = "tester"
    connection_identity = {"base_url": "http://localhost:8080/zentao", "account": "tester"}

    def __init__(self, *, related: bool = True):
        self.projects = [{"id": 12, "name": "商城", **({"products": [3]} if related else {})}]
        self.products = [{"id": 3, "name": "商城产品", "modules": [{"id": 45}],
                          **({"projects": [12]} if related else {})}]
        self.builds = [{"id": 7, "name": "release-7"}]
        self.users = [
            {"id": 1, "account": "tester", "realname": "测试员"},
            {"id": 2, "account": "frontend", "realname": "王五"},
            {"id": 3, "account": "backend", "realname": "赵六"},
        ]

    def list_all(self, resource, *, scope=None, scope_id=None, browse=None, per_page=1000, preserve_partial=False):
        rows = {"project": self.projects, "product": self.products, "build": self.builds,
                "user": self.users}[resource]
        if resource == "build" and scope_id != 12:
            rows = []
        return SimpleNamespace(items=list(rows), complete=True, partial_failures=[])

    def view(self, resource, item_id):
        return self.products[0] if resource == "product" and item_id == 3 else None


class ProjectConfigTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.client = FakeClient()

    def configure_project(self):
        return project_set(self.client, alias="mall", project="12", product="3", default_build="trunk", root=self.root)

    def test_project_module_context_persist_and_preserve_modules(self):
        result = self.configure_project()
        self.assertEqual(12, result["project"]["project_id"])
        self.assertTrue(result["complete"])
        module_result = module_set(self.client, project_alias="mall", alias="payment", module="45",
                                   frontend="王五", backend="赵六", root=self.root)
        self.assertEqual("frontend", module_result["module"]["frontend_account"])
        self.assertTrue(module_result["complete"])
        context = context_use(self.client, project_alias="mall", module_alias="payment", root=self.root)
        self.assertEqual({"project_alias": "mall", "module_alias": "payment"}, context["current"])
        reloaded = context_view(self.client, root=self.root)
        self.assertEqual("backend", reloaded["module"]["backend_account"])
        self.assertEqual("trunk", reloaded["project"]["default_affected_build"])
        listed = project_list(self.client, root=self.root)
        self.assertEqual(["payment"], listed["projects"][0]["module_aliases"])
        files = list((self.root / "testing-projects").glob("*.json"))
        self.assertEqual(1, len(files))
        self.assertEqual("tester", json.loads(files[0].read_text())["owner"]["account"])
        if os.name == "posix":
            self.assertEqual(0o700, stat.S_IMODE(files[0].parent.stat().st_mode))
            self.assertEqual(0o600, stat.S_IMODE(files[0].stat().st_mode))
        project_set(self.client, alias="mall", project="12", product="3", default_build="7", root=self.root)
        self.assertTrue(context_view(self.client, root=self.root)["module"]["stale"])

    def test_current_delete_is_explicitly_cleared(self):
        self.configure_project()
        module_set(self.client, project_alias="mall", alias="payment", module="45", frontend="王五", backend="赵六", root=self.root)
        context_use(self.client, project_alias="mall", module_alias="payment", root=self.root)
        module_remove(self.client, project_alias="mall", alias="payment", root=self.root)
        with self.assertRaises(TestingConfigError) as error:
            context_view(self.client, root=self.root)
        self.assertEqual("CURRENT_MODULE_MISSING", error.exception.code)
        project_remove(self.client, "mall", root=self.root)
        listed = project_list(self.client, root=self.root)
        self.assertEqual([], listed["projects"])
        self.assertEqual({"project_alias": None, "module_alias": None}, listed["current"])

    def test_build_and_user_validation_fail_without_overwriting_old_config(self):
        self.configure_project()
        path = next((self.root / "testing-projects").glob("*.json"))
        before = path.read_bytes()
        with self.assertRaises(TestingConfigError) as error:
            project_set(self.client, alias="mall", project="12", product="3", default_build="999", root=self.root)
        self.assertEqual("BUILD_NOT_FOUND", error.exception.code)
        self.assertEqual(before, path.read_bytes())
        self.client.users.append({"id": 4, "account": "other", "realname": "王五"})
        with self.assertRaises(TestingConfigError) as error:
            module_set(self.client, project_alias="mall", alias="payment", module="45", frontend="王五", backend="赵六", root=self.root)
        self.assertEqual("USER_AMBIGUOUS", error.exception.code)
        self.assertEqual(before, path.read_bytes())

    def test_relation_gap_is_explicit_and_not_claimed_verified(self):
        result = project_set(FakeClient(related=False), alias="mall", project="12", product="3", default_build="trunk", root=self.root)
        self.assertEqual("unverified", result["project"]["verification"]["project_product"])
        self.assertEqual("PROJECT_PRODUCT_UNVERIFIED", result["partial_failures"][0]["code"])

    def test_missing_project_id_does_not_require_project_association(self):
        result = project_set(FakeClient(related=False), alias="product-only", project=None, product="3",
                             default_build="7", root=self.root)
        self.assertIsNone(result["project"]["project_id"])
        self.assertEqual("not_applicable", result["project"]["verification"]["project_product"])
        self.assertTrue(result["complete"])
        self.assertEqual([], result["partial_failures"])

    def test_alias_case_collision_is_rejected(self):
        self.configure_project()
        with self.assertRaises(TestingConfigError) as error:
            project_set(self.client, alias="MALL", project="12", product="3", default_build="trunk", root=self.root)
        self.assertEqual("ALIAS_CONFLICT", error.exception.code)

    def test_module_product_mismatch_is_rejected_without_creating_config(self):
        self.configure_project()
        with self.assertRaises(TestingConfigError) as error:
            module_set(self.client, project_alias="mall", alias="bad", module="99",
                       frontend="王五", backend="赵六", root=self.root)
        self.assertEqual("MODULE_PRODUCT_MISMATCH", error.exception.code)
        self.assertEqual([], project_list(self.client, root=self.root)["projects"][0]["module_aliases"])

    def test_conflicting_directory_duplicate_is_rejected(self):
        self.client.projects.append({"id": 12, "name": "另一个名称", "products": [3]})
        with self.assertRaises(TestingConfigError) as error:
            self.configure_project()
        self.assertEqual("DIRECTORY_CONFLICT", error.exception.code)


if __name__ == "__main__":
    unittest.main()
