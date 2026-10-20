from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "zentao-bug-board" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from board import build_board, collect_board, render_board  # noqa: E402
from workdays import next_workday  # noqa: E402


TZ = ZoneInfo("Asia/Shanghai")


def bug(bug_id, opened, pri=1, status="active", assigned="dev", **extra):
    return {"id": bug_id, "title": f"Bug {bug_id}", "openedDate": opened,
            "pri": pri, "status": status, "assignedTo": assigned, **extra}


class BoardRulesTests(unittest.TestCase):
    def test_classifies_one_snapshot_by_state_cutoff_and_deadline(self):
        rows = [
            bug(1, "2026-10-20 15:59:59", 1),
            bug(2, "2026-10-20 16:00:00", 1),
            bug(3, "2026-10-20 16:01:00", 1, status="resolved", assigned="qa", resolvedBy="dev"),
            bug(4, "2026-10-20 16:01:00", 1, status="closed"),
            bug(5, "2026-10-19 17:00:00", 2),
            bug(6, "2026-10-19 15:00:00", 2),
            bug(7, "2026-10-19 15:00:00", 3),
            bug(8, "2026-10-20 15:00:00", 4),
            bug(9, "2026-10-20 15:00:00", 0),
            bug(1, "2026-10-20 15:59:59", 1),
        ]
        report = build_board(12, "Alpha", rows, datetime(2026, 10, 20, 16, 1, tzinfo=TZ))
        self.assertEqual([9, 1, 5], [r["id"] for r in report["queues"]["today"]])
        self.assertEqual([8], [r["id"] for r in report["queues"]["next_workday"]])
        self.assertEqual([2], [r["id"] for r in report["queues"]["after_1600"]])
        self.assertEqual([3], [r["id"] for r in report["queues"]["awaiting_test"]])
        self.assertEqual([6, 7], [r["id"] for r in report["queues"]["overdue"]])
        self.assertEqual([], report["queues"]["uncertain"])
        self.assertNotIn(4, [r["id"] for queue in report["queues"].values() for r in queue])
        self.assertEqual("qa", report["queues"]["awaiting_test"][0]["test_owner"])
        self.assertEqual("dev", report["queues"]["awaiting_test"][0]["resolved_by"])
        self.assertEqual("2026-10-21 12:00", report["queues"]["next_workday"][0]["due"])
        self.assertEqual(1, report["duplicates"])

    def test_china_statutory_calendar_includes_makeup_weekends_and_holidays(self):
        self.assertEqual("2026-10-10", str(next_workday("2026-10-09")))
        self.assertEqual("2026-10-08", str(next_workday("2026-09-30")))
        self.assertEqual("2025-01-26", str(next_workday("2025-01-25")))
        self.assertEqual("2025-04-07", str(next_workday("2025-04-03")))
        self.assertEqual("2026-01-04", str(next_workday("2025-12-31")))
        self.assertIsNone(next_workday("2026-12-31"))

    def test_noon_boundary_and_missing_calendar_are_explicit(self):
        rows = [bug(1, "2026-10-19 15:00:00", 3)]
        before = build_board(12, "Alpha", rows, datetime(2026, 10, 20, 11, 59, tzinfo=TZ))
        at_noon = build_board(12, "Alpha", rows, datetime(2026, 10, 20, 12, 0, tzinfo=TZ))
        self.assertEqual([1], [r["id"] for r in before["queues"]["next_workday"]])
        self.assertEqual([1], [r["id"] for r in at_noon["queues"]["overdue"]])
        future = build_board(12, "Alpha", [bug(2, "2026-12-31 15:00:00", 3)],
                             datetime(2026, 12, 31, 16, 1, tzinfo=TZ))
        self.assertEqual([2], [r["id"] for r in future["queues"]["uncertain"]])
        self.assertFalse(future["complete"])

    def test_bad_fields_are_visible_and_never_invent_owners(self):
        rows = [bug(1, "2026-10-20", 1), bug(2, "2026-10-20 15:00:00", "bad"),
                bug(3, "2026-10-20 15:00:00", 1, status="mystery"),
                bug(4, "2026-10-20 15:00:00", 1, assigned="")]
        report = build_board(12, "Alpha", rows, datetime(2026, 10, 20, 16, 1, tzinfo=TZ))
        self.assertEqual([3, 1, 2], [r["id"] for r in report["queues"]["uncertain"]])
        self.assertIsNone(report["queues"]["today"][0]["dev_owner"])
        self.assertFalse(report["complete"])

    def test_partial_pages_and_id_mapped_links_remain_visible(self):
        class Listed:
            def __init__(self, items, complete=True, failures=()):
                self.items = items
                self.complete = complete
                self.partial_failures = list(failures)

        class Client:
            def __init__(self):
                self.calls = []

            def list_all(self, resource, **kwargs):
                self.calls.append((resource, kwargs))
                if resource == "project":
                    return Listed([{"id": 12, "name": "Alpha"}])
                return Listed([bug(4, "2026-10-20 15:00:00"),
                               bug(2, "2026-10-20 15:00:00", status="resolved")],
                              False, [{"code": "PAGE_READ_FAILED", "page": 2}])

            def bug_web_urls(self, ids):
                self.calls.append(("urls", ids))
                return [{"id": 2, "url": "https://example.test/2"},
                        {"id": 4, "url": "https://example.test/4"}]

        client = Client()
        report = collect_board(client, 12, datetime(2026, 10, 20, 16, 1, tzinfo=TZ))
        self.assertFalse(report["complete"])
        self.assertEqual([{"code": "PAGE_READ_FAILED", "page": 2}], report["partial_failures"])
        self.assertEqual("https://example.test/4", report["queues"]["today"][0]["url"])
        self.assertEqual("https://example.test/2", report["queues"]["awaiting_test"][0]["url"])
        self.assertEqual(("bug", {"scope": "project", "scope_id": 12, "browse": "all",
                                  "preserve_partial": True}), client.calls[1])
        markdown = render_board(report)
        self.assertIn("[4](https://example.test/4)", markdown)
        self.assertIn("查询不完整", markdown)
        self.assertNotIn("已关闭", markdown)

    def test_empty_project_and_ambiguous_project_identity(self):
        class Listed:
            def __init__(self, rows):
                self.items, self.complete, self.partial_failures = rows, True, []

        class Client:
            def __init__(self, projects):
                self.projects = projects
                self.calls = []

            def list_all(self, resource, **kwargs):
                self.calls.append(resource)
                return Listed(self.projects if resource == "project" else [])

        empty = Client([{"id": 12, "name": "Alpha"}])
        report = collect_board(empty, 12, datetime(2026, 10, 20, 16, 1, tzinfo=TZ))
        self.assertTrue(report["complete"])
        self.assertTrue(all(count == 0 for count in report["counts"].values()))
        self.assertEqual(["project", "bug"], empty.calls)
        repeated = Client([{"id": 12, "name": "Alpha"}, {"id": "12", "name": "Alpha"}])
        self.assertTrue(collect_board(repeated, 12, datetime(2026, 10, 20, 16, 1, tzinfo=TZ))["complete"])
        ambiguous = Client([{"id": 12, "name": "Alpha"}, {"id": 12, "name": "Alpha copy"}])
        with self.assertRaisesRegex(ValueError, "唯一确认"):
            collect_board(ambiguous, 12, datetime(2026, 10, 20, 16, 1, tzinfo=TZ))
        self.assertEqual(["project"], ambiguous.calls)

    def test_conflicting_duplicate_is_not_silent(self):
        rows = [bug(1, "2026-10-20 15:00:00"), bug(1, "2026-10-20 15:00:00", pri=2)]
        report = build_board(12, "Alpha", rows, datetime(2026, 10, 20, 16, 1, tzinfo=TZ))
        self.assertEqual(1, report["counts"]["today"])
        self.assertFalse(report["complete"])
        self.assertIn("DUPLICATE_CONFLICT", [warning["code"] for warning in report["data_warnings"]])

    def test_markdown_escapes_untrusted_title(self):
        report = build_board(12, "Alpha", [bug(1, "2026-10-20 15:00:00", title="<script>|x")],
                             datetime(2026, 10, 20, 16, 1, tzinfo=TZ))
        rendered = render_board(report)
        self.assertIn("&lt;script&gt;\\|x", rendered)
        self.assertNotIn("<script>", rendered)

    def test_invalid_id_does_not_break_links_for_other_bugs(self):
        class Listed:
            def __init__(self, rows):
                self.items, self.complete, self.partial_failures = rows, True, []

        class Client:
            def list_all(self, resource, **kwargs):
                return Listed([{"id": 12, "name": "Alpha"}] if resource == "project" else [
                    bug(0, "2026-10-20 15:00:00"), bug(2, "2026-10-20 15:00:00")])

            def bug_web_urls(self, ids):
                self_ids = ids
                if self_ids != [2]:
                    raise AssertionError(self_ids)
                return []

        report = collect_board(Client(), 12, datetime(2026, 10, 20, 16, 1, tzinfo=TZ))
        self.assertEqual([0], [row["id"] for row in report["queues"]["uncertain"]])
        self.assertEqual([2], [row["id"] for row in report["queues"]["today"]])
        self.assertFalse(report["complete"])
        self.assertIn("BUG_URL_FAILED", [warning["code"] for warning in report["data_warnings"]])


if __name__ == "__main__":
    unittest.main()
