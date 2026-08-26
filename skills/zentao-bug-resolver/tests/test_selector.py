from __future__ import annotations

import argparse
import importlib.util
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "zentao_bug_resolver.py"
spec = importlib.util.spec_from_file_location("zentao_bug_resolver", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def args(**values: object) -> argparse.Namespace:
    defaults = {
        "bug_id": None, "user": None, "product": None, "project": None, "execution": None,
        "module": None, "status": [], "priority": [], "severity": [], "created_after": None,
        "created_before": None, "updated_after": None, "updated_before": None, "browse": None, "per_page": 2,
    }
    defaults.update(values)
    return argparse.Namespace(**defaults)


class StubClient:
    def __init__(self, pages: dict[tuple[str, str | None, int | None, int], object]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, str | None, int | None, int]] = []

    def list_page(self, resource: str, *, scope: str | None = None, scope_id: int | None = None,
                  page: int = 1, per_page: int = 1000, browse: str | None = None) -> dict[str, object]:
        key = (resource, scope, scope_id, page)
        self.calls.append(key)
        value = self.pages.get(key, {mod.COLLECTIONS[resource]: [], "pager": {"total": 0}})
        if isinstance(value, Exception):
            raise value
        return value  # type: ignore[return-value]


class SelectorTests(unittest.TestCase):
    def test_explicit_ids_keep_order_and_do_not_read(self) -> None:
        client = StubClient({})
        result = mod.select_bugs(client, args(bug_id=[9, 7, 9, 11]))
        self.assertEqual("ids", result["mode"])
        self.assertEqual(9, result["current_bug_id"])
        self.assertEqual([7, 11], result["pending_queue"])
        self.assertEqual(1, result["duplicates_removed"])
        self.assertEqual([], client.calls)

    def test_scoped_query_filters_and_sorts(self) -> None:
        client = StubClient({
            ("bug", "product", 1, 1): {"bugs": [
                {"id": 4, "assignedTo": "alice", "status": "active", "severity": 2},
                {"id": 2, "assignedTo": "alice", "status": "active", "severity": 1},
            ], "pager": {"total": 3}},
            ("bug", "product", 1, 2): {"bugs": [
                {"id": 2, "assignedTo": "alice", "status": "active", "severity": 1},
                {"id": 1, "assignedTo": "bob", "status": "active", "severity": 1},
            ], "pager": {"total": 3}},
            ("user", None, None, 1): {"users": [{"id": 8, "account": "alice", "realname": "张三"}], "pager": {"total": 1}},
        })
        result = mod.select_bugs(client, args(product="1", user="张三", severity=["1"]))
        self.assertEqual([2], result["pending_queue"] + [result["current_bug_id"]])
        self.assertTrue(result["complete"])
        self.assertEqual(4, result["pages"])

    def test_mid_page_failure_retains_previous_rows(self) -> None:
        client = StubClient({
            ("bug", "execution", 3, 1): {"bugs": [{"id": 4}], "pager": {"total": 3}},
            ("bug", "execution", 3, 2): RuntimeError("page unavailable"),
        })
        result = mod.select_bugs(client, args(execution="3"))
        self.assertEqual([4], result["pending_queue"] + [result["current_bug_id"]])
        self.assertFalse(result["complete"])
        self.assertEqual("PAGE_READ_FAILED", result["partial_failures"][0]["code"])
        self.assertEqual(1, result["pages"])
        self.assertEqual(2, len(client.calls))

    def test_missing_filter_field_is_not_silent(self) -> None:
        rows = [{"id": 1, "severity": 1}, {"id": 2, "title": "unknown"}]
        matched, unsupported = mod.filter_records(rows, severities=["1"])
        self.assertEqual([1], [row["id"] for row in matched])
        self.assertFalse(not unsupported)
        self.assertEqual(["2"], unsupported[0]["missing_ids"])

    def test_name_ambiguity_and_module_validation(self) -> None:
        client = StubClient({
            ("product", None, None, 1): {"products": [{"id": 1, "name": "WebHub"}, {"id": 2, "name": "WebHub"}], "pager": {"total": 2}},
        })
        with self.assertRaises(mod.AmbiguousMatchError):
            mod.select_bugs(client, args(product="WebHub"))
        with self.assertRaises(argparse.ArgumentTypeError):
            mod._positive_int("abc")

    def test_multiple_scopes_are_rejected_instead_of_ignored(self) -> None:
        client = StubClient({})
        with self.assertRaises(ValueError):
            mod.select_bugs(client, args(product="1", project="2"))
        self.assertEqual([], client.calls)

    def test_module_filter_uses_only_numeric_ids(self) -> None:
        rows = [
            {"id": 1, "module": {"id": 3, "name": "Core"}},
            {"id": 2, "module": "Core", "moduleID": 3},
            {"id": 3, "module": "Core"},
        ]
        matched, unsupported = mod.filter_records(rows, module=3)
        self.assertEqual([1, 2], [row["id"] for row in matched])
        self.assertEqual(["3"], unsupported[0]["missing_ids"])

    def test_time_boundaries_and_invalid_values(self) -> None:
        rows = [
            {"id": 1, "openedDate": "2026-08-25"},
            {"id": 2, "openedDate": "2026-08-26"},
            {"id": 3, "openedDate": "2026-08-26T23:59:59"},
            {"id": 4},
        ]
        matched, unsupported = mod.filter_records(rows, created_after="2026-08-25", created_before="2026-08-26")
        self.assertEqual([1, 2, 3], [row["id"] for row in matched])
        self.assertEqual(["4"], unsupported[0]["missing_ids"])
        with self.assertRaises(ValueError):
            mod.filter_records(rows, created_after="not-a-date")

    def test_global_query_continues_after_one_product_failure(self) -> None:
        client = StubClient({
            ("product", None, None, 1): {"products": [{"id": 1}, {"id": 2}], "pager": {"total": 2}},
            ("bug", "product", 1, 1): RuntimeError("product one failed"),
            ("bug", "product", 2, 1): {"bugs": [{"id": 7, "status": "active"}], "pager": {"total": 1}},
        })
        result = mod.select_bugs(client, args(status=["active"]))
        self.assertEqual(7, result["current_bug_id"])
        self.assertFalse(result["complete"])
        self.assertEqual("PAGE_READ_FAILED", result["partial_failures"][0]["code"])


if __name__ == "__main__":
    unittest.main()
