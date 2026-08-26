from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "zentao_bug_resolver.py"
spec = importlib.util.spec_from_file_location("zentao_bug_resolver", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class ViewClient:
    def __init__(self, value: object) -> None:
        self.value = value
        self.calls: list[tuple[str, int]] = []

    def view(self, resource: str, item_id: int) -> object:
        self.calls.append((resource, item_id))
        return self.value


class SnapshotTests(unittest.TestCase):
    def complete_bug(self, **overrides: object) -> dict[str, object]:
        bug: dict[str, object] = {
            "id": 1, "status": "active", "assignedTo": "alice", "title": "same",
            "steps": "repro", "severity": 2, "pri": 1, "product": 1, "project": 2,
            "execution": 3, "module": 4, "openedBuild": "build-1", "openedByAccount": "alice",
            "openedDate": "2026-08-25T10:00:00", "lastEditedDate": "2026-08-25T11:00:00",
        }
        bug.update(overrides)
        return bug

    def test_snapshot_preserves_raw_bug_and_marks_missing_fields(self) -> None:
        raw = {"id": 12, "status": "active", "title": "Button", "unknown": "kept"}
        snapshot = mod.build_snapshot(12, raw)
        self.assertIs(snapshot["bug"], raw)
        self.assertEqual(12, snapshot["critical"]["id"])
        self.assertEqual("active", snapshot["critical"]["status"])
        self.assertIsNone(snapshot["critical"]["severity"])
        self.assertIn("severity", snapshot["unavailable_fields"])
        self.assertIn("unknown", snapshot["bug"])

    def test_creator_account_requires_explicit_account_evidence(self) -> None:
        self.assertEqual("alice", mod.extract_creator_account({"openedBy": {"account": "alice", "realname": "张三"}}))
        self.assertEqual("alice", mod.extract_creator_account({"openedByAccount": "alice"}))
        self.assertIsNone(mod.extract_creator_account({"openedBy": "张三", "creator": "张三"}))
        self.assertIsNone(mod.build_snapshot(1, {"id": 1, "openedBy": "张三"})["critical"]["creator_account"])

    def test_compare_unchanged_critical_projection(self) -> None:
        raw = self.complete_bug(unrelated="new")
        baseline = mod.build_snapshot(1, raw)
        result = mod.compare_snapshots(1, baseline, {**raw, "unrelated": "new"})
        self.assertFalse(result["changed"])
        self.assertFalse(result["comparison_blocked"])
        self.assertEqual([], result["changes"])

    def test_compare_reports_each_critical_change(self) -> None:
        baseline = mod.build_snapshot(1, self.complete_bug(steps="old"))
        current = self.complete_bug(status="resolved", assignedTo="bob", steps="new")
        result = mod.compare_snapshots(1, baseline, current)
        self.assertTrue(result["changed"])
        self.assertFalse(result["comparison_blocked"])
        self.assertEqual(
            ["status", "assignee", "description"],
            [change["field"] for change in result["changes"]],
        )
        self.assertEqual("active", result["changes"][0]["before"])
        self.assertEqual("resolved", result["changes"][0]["after"])

    def test_disappearing_observable_field_is_a_conflict(self) -> None:
        baseline = mod.build_snapshot(1, self.complete_bug(severity=1))
        current = self.complete_bug()
        del current["severity"]
        result = mod.compare_snapshots(1, baseline, current)
        self.assertTrue(result["changed"])
        self.assertTrue(result["comparison_blocked"])
        self.assertEqual("severity", result["changes"][0]["field"])
        self.assertIsNone(result["changes"][0]["after"])

    def test_missing_critical_field_on_both_sides_blocks_unchanged_result(self) -> None:
        raw = self.complete_bug()
        del raw["severity"]
        baseline = mod.build_snapshot(1, raw)
        result = mod.compare_snapshots(1, baseline, dict(raw))
        self.assertTrue(result["changed"])
        self.assertTrue(result["comparison_blocked"])
        self.assertEqual("CRITICAL_FIELD_UNAVAILABLE", result["block_reason"])
        self.assertIn("severity", result["unavailable_fields"])
        self.assertEqual([], result["changes"])

    def test_malformed_or_wrong_baseline_is_rejected(self) -> None:
        current = {"id": 1}
        with self.assertRaises(ValueError):
            mod.compare_snapshots(1, {"bug_id": 2, "critical": {}}, current)
        with self.assertRaises(ValueError):
            mod.compare_snapshots(1, {"bug_id": 1, "critical": {}}, current)
        valid = mod.build_snapshot(1, current)
        valid["bug_id"] = True
        with self.assertRaises(ValueError):
            mod.compare_snapshots(1, valid, current)
        valid = mod.build_snapshot(1, current)
        del valid["bug"]
        with self.assertRaises(ValueError):
            mod.compare_snapshots(1, valid, current)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            handle.write("not-json")
            handle.flush()
            with self.assertRaises(ValueError):
                mod._read_baseline(handle.name, 1)

    def test_view_path_is_read_only_and_rejects_non_object(self) -> None:
        client = ViewClient({"id": 1, "status": "active"})
        payload = mod.build_snapshot(1, client.view("bug", 1))
        self.assertEqual(1, payload["bug_id"])
        self.assertEqual([("bug", 1)], client.calls)
        with self.assertRaises(ValueError):
            mod.build_snapshot(1, ViewClient(None).view("bug", 1))

    def test_snapshot_payload_is_json_serializable(self) -> None:
        payload = mod.build_snapshot(4, {"id": 4, "openedBy": {"account": "alice"}, "status": "active"})
        self.assertEqual(payload, json.loads(json.dumps(payload, ensure_ascii=False)))


if __name__ == "__main__":
    unittest.main()
