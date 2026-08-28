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

    def test_creator_account_rejects_conflicts_and_malformed_evidence(self) -> None:
        for raw in (
            {"openedByAccount": "alice", "creatorAccount": "bob"},
            {"openedByAccount": "alice", "openedBy": {"account": "bob"}},
            {"openedBy": {"account": ["alice"]}},
            {"openedByAccount": True}, {"creatorAccount": 42},
            {"openedByAccount": "   "}, {"openedByAccount": " alice"},
            {"openedByAccount": "closed"},
            {"openedByAccount": "alice", "creator": []},
            {"openedByAccount": "alice", "creatorAccount": {}},
        ):
            with self.subTest(raw=raw):
                self.assertIsNone(mod.extract_creator_account(raw))
                self.assertIn("creator_account", mod.build_snapshot(1, raw)["unavailable_fields"])
        self.assertEqual("alice", mod.extract_creator_account({
            "openedByAccount": "alice", "creator": {"account": "alice"},
        }))

    def test_human_assignee_defaults_to_creator_but_explicit_user_wins(self) -> None:
        bug = {"openedBy": {"account": "creator"}}
        self.assertEqual("creator", mod.resolve_human_assignee(bug))
        users = [{"id": 2, "account": "tester", "realname": "张三"}]
        for value in ("tester", "张三", "TESTER"):
            for raw in (bug, {}):
                with self.subTest(value=value, raw=raw):
                    self.assertEqual("tester", mod.resolve_human_assignee(
                        raw, explicit_assignee=value, users=users, users_complete=True,
                    ))

    def test_human_assignee_fails_closed_without_fallback(self) -> None:
        for raw in ({}, {"openedBy": "张三"}, {"openedByAccount": "alice", "creatorAccount": "bob"}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                mod.resolve_human_assignee(raw)
        bug = {"openedByAccount": "creator"}
        for value, users, complete in (
            ("nobody", [], True),
            ("", [], True),
            ("张三", [{"account": "a", "realname": "张三"}, {"account": "b", "realname": "张三"}], True),
            ("a", [{"account": "a"}], False),
            ("张三", [{"account": ["a"], "realname": "张三"}], True),
            ("张三", [{"realname": "张三"}], True),
            ("a", [{"account": "a", "realname": ["张三"]}], True),
            ("a", [{"id": 1, "account": "a"}, {"id": 1, "account": "b"}], True),
        ):
            with self.subTest(value=value, users=users, complete=complete), self.assertRaises(ValueError):
                mod.resolve_human_assignee(bug, explicit_assignee=value, users=users, users_complete=complete)

    def test_opened_by_string_is_verified_by_exact_directory_account(self) -> None:
        bug = {"openedBy": "dongyanrong"}
        users = [
            {"id": 1, "account": "dongyanrong", "realname": "董燕荣"},
            {"id": 2, "account": "other", "realname": "dongyanrong"},
        ]
        self.assertEqual("dongyanrong", mod.resolve_human_assignee(bug, users=users, users_complete=True))
        self.assertEqual("dongyanrong", mod.extract_creator_account(bug, users=users, users_complete=True))
        self.assertIsNone(mod.extract_creator_account(bug))

    def test_opened_by_string_does_not_use_name_case_fallback_or_partial_directory(self) -> None:
        for candidate, users, complete in (
            ("dongyanrong", [], True),
            ("董燕荣", [{"account": "dongyanrong", "realname": "董燕荣"}], True),
            ("DONGYANRONG", [{"account": "dongyanrong"}], True),
            ("dongyanrong", [{"account": "dongyanrong"}], False),
            ("dongyanrong", [{"id": 1, "account": "dongyanrong"}, {"id": 2, "account": "dongyanrong"}], True),
        ):
            with self.subTest(candidate=candidate, users=users, complete=complete), self.assertRaises(ValueError):
                mod.resolve_human_assignee({"openedBy": candidate}, users=users, users_complete=complete)

    def test_opened_by_string_must_agree_with_other_creator_evidence(self) -> None:
        users = [{"account": "dongyanrong"}, {"account": "other"}]
        for explicit in ("dongyanrong", "other"):
            bug = {"openedBy": "dongyanrong", "openedByAccount": explicit}
            with self.subTest(explicit=explicit):
                if explicit == "dongyanrong":
                    self.assertEqual(explicit, mod.resolve_human_assignee(bug, users=users, users_complete=True))
                else:
                    with self.assertRaises(ValueError):
                        mod.resolve_human_assignee(bug, users=users, users_complete=True)
        with self.assertRaises(ValueError):
            mod.resolve_human_assignee({"openedBy": "missing", "openedByAccount": "other"}, users=users, users_complete=True)

    def test_explicit_assignee_overrides_unverified_opened_by_string(self) -> None:
        self.assertEqual("tester", mod.resolve_human_assignee(
            {"openedBy": "not-in-directory"}, explicit_assignee="张三",
            users=[{"account": "tester", "realname": "张三"}], users_complete=True,
        ))

    def test_human_readback_requires_resolved_and_explicit_account(self) -> None:
        for assignment in ("alice", {"account": "alice", "realname": "张三"}):
            self.assertTrue(mod.human_readback_matches({"status": "resolved", "assignedTo": assignment}, "alice"))
        for raw in (
            {"status": "active", "assignedTo": "alice"},
            {"status": "closed", "assignedTo": "alice"},
            {"status": "resolved", "assignedTo": "bob"},
            {"status": "resolved"},
            {"status": "resolved", "assignedTo": {"realname": "alice"}},
            {"status": "resolved", "assignedTo": {"id": "alice"}},
            {"status": "resolved", "assignedTo": ["alice"]},
        ):
            with self.subTest(raw=raw):
                self.assertFalse(mod.human_readback_matches(raw, "alice"))

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
        payload = mod.build_snapshot(1, mod._read_view(client, 1))
        self.assertEqual(1, payload["bug_id"])
        self.assertEqual([("bug", 1)], client.calls)
        with self.assertRaises(ValueError):
            mod._read_view(ViewClient(None), 1)

    def test_read_view_unwraps_api_bug_payload(self) -> None:
        client = ViewClient({"bug": self.complete_bug(), "status": "success"})
        payload = mod.build_snapshot(1, mod._read_view(client, 1))
        self.assertEqual(1, payload["critical"]["id"])
        self.assertEqual("same", payload["critical"]["title"])
        self.assertEqual([], payload["unavailable_fields"])
        self.assertEqual([("bug", 1)], client.calls)

    def test_read_view_rejects_malformed_wrapped_payload(self) -> None:
        with self.assertRaises(ValueError):
            mod._read_view(ViewClient({"bug": None, "status": "success"}), 1)

    def test_snapshot_payload_is_json_serializable(self) -> None:
        payload = mod.build_snapshot(4, {"id": 4, "openedBy": {"account": "alice"}, "status": "active"})
        self.assertEqual(payload, json.loads(json.dumps(payload, ensure_ascii=False)))


if __name__ == "__main__":
    unittest.main()
