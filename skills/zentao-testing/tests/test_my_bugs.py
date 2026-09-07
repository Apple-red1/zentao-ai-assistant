from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from my_bugs import collect_my_bugs
from presenter import render_my_bugs
from project_config import context_use, module_set, project_set


class FakeClient:
    account = "tester"
    connection_identity = {"base_url": "http://localhost:8080/zentao", "account": "tester"}

    def __init__(self):
        self.bug_scopes = []
        self.bugs = [
            {"id": 4, "title": "closed", "status": "closed", "assignedTo": "tester", "pri": 1, "severity": 1},
            {"id": 3, "title": "backend", "status": "active", "assignedTo": "tester", "pri": 2, "severity": 1, "module": 45},
            {"id": 2, "title": "other", "status": "active", "assignedTo": "other", "pri": 1, "severity": 1},
            {"id": 1, "title": "resolved", "status": "resolved", "assignedTo": {"account": "tester"}, "pri": 1, "severity": 2},
            {"id": "3", "title": "backend", "status": "active", "assignedTo": "tester", "pri": 2, "severity": 1, "module": 45},
        ]

    def list_all(self, resource, *, scope=None, scope_id=None, browse=None, per_page=1000, preserve_partial=False):
        if resource == "project":
            return SimpleNamespace(items=[{"id": 12, "name": "商城", "products": [3]}], complete=True, partial_failures=[])
        if resource == "product":
            return SimpleNamespace(items=[{"id": 3, "name": "产品", "projects": [12]}], complete=True, partial_failures=[])
        if resource == "execution":
            return SimpleNamespace(items=[], complete=True, partial_failures=[])
        if resource == "user":
            return SimpleNamespace(items=[{"id": 1, "account": "tester", "realname": "测试员"}], complete=True, partial_failures=[])
        if resource == "bug":
            self.bug_scopes.append((scope, scope_id))
            return SimpleNamespace(items=list(self.bugs), complete=True, partial_failures=[])
        raise AssertionError(resource)

    def bug_web_urls(self, ids):
        return [{"id": ident, "url": f"http://localhost/index.php?m=bug&f=view&bugID={ident}"} for ident in ids]

    def view(self, resource, item_id):
        return {"modules": [{"id": 45}]} if resource == "product" and item_id == 3 else None


class MyBugsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.client = FakeClient()
        project_set(self.client, alias="mall", project="12", product="3", default_build="trunk", root=self.root)
        module_set(self.client, project_alias="mall", alias="payment", module="45", frontend="tester", backend="tester", root=self.root)
        context_use(self.client, project_alias="mall", module_alias="payment", root=self.root)

    def test_current_project_filters_closed_and_other_accounts_dedupes_and_sorts(self):
        result = collect_my_bugs(self.client, root=self.root)
        self.assertTrue(result["complete"])
        self.assertEqual([3, 1], [item["id"] for item in result["items"]])
        self.assertEqual(1, result["duplicates_removed"])
        self.assertIn("| Bug ID | 标题 | 状态 | 优先级 | 严重程度 | 当前指派 | 解决人 | 创建时间 | 解决时间 |", render_my_bugs(result))
        self.assertIn("[3](http://localhost/index.php?m=bug&f=view&bugID=3)", render_my_bugs(result))

    def test_current_project_does_not_default_to_current_module(self):
        self.client.bugs.append({"id": 5, "title": "other module", "status": "active", "assignedTo": "tester", "pri": 3, "severity": 3, "module": 99})
        result = collect_my_bugs(self.client, root=self.root)
        self.assertEqual([3, 5, 1], [item["id"] for item in result["items"]])
        filtered = collect_my_bugs(self.client, module_id=45, root=self.root)
        self.assertEqual([3], [item["id"] for item in filtered["items"]])

    def test_missing_project_id_reads_current_product_scope(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        client = FakeClient()
        project_set(client, alias="product-only", project=None, product="3", default_build="7", root=root)
        module_set(client, project_alias="product-only", alias="payment", module="45",
                   frontend="tester", backend="tester", root=root)
        context_use(client, project_alias="product-only", module_alias="payment", root=root)
        result = collect_my_bugs(client, root=root)
        self.assertTrue(result["complete"])
        self.assertEqual("current_product", result["scope"]["mode"])
        self.assertEqual(3, result["scope"]["product_id"])
        self.assertEqual([("product", 3)], client.bug_scopes)


if __name__ == "__main__":
    unittest.main()
