from __future__ import annotations

import importlib.util
import unittest
from types import SimpleNamespace
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'zentao_statistics.py'
spec = importlib.util.spec_from_file_location('zentao_statistics', MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class StatisticsTests(unittest.TestCase):
    def test_bug_summary_is_deterministic_and_deduplicates_ids(self) -> None:
        records = [
            {'id': 2, 'status': 'resolved', 'assignedTo': 'bob', 'pri': 2, 'severity': 1},
            {'id': 1, 'status': 'active', 'assignedTo': 'alice', 'pri': 1, 'severity': 2},
            {'id': 2, 'status': 'resolved', 'assignedTo': 'bob', 'pri': 2, 'severity': 1},
        ]
        result = mod.summarize_records('bug', records, complete=True)
        self.assertEqual(2, result['total'])
        self.assertEqual({'active': 1, 'resolved': 1}, result['by_status'])
        self.assertEqual({'alice': 1, 'bob': 1}, result['by_assignee'])
        self.assertEqual({'1': 1, '2': 1}, result['by_priority'])
        self.assertEqual({'1': 1, '2': 1}, result['by_severity'])
        self.assertTrue(result['complete'])
        self.assertEqual(1, result['duplicates_removed'])


    def test_summary_defaults_to_full_browse_semantics(self) -> None:
        calls = []
        class Client:
            def list_all(self, resource, **kwargs):
                calls.append((resource, kwargs))
                return SimpleNamespace(items=[], complete=True, partial_failures=[], pages=1)
        mod._load_summary(Client(), 'story', 'product', 1, browse=None, per_page=1000, today=None, cache_data=False)
        self.assertEqual('all-story', calls[0][1]['browse'])

    def test_assignee_summary_explicitly_groups_empty_and_closed_values_as_unassigned(self) -> None:
        result = mod.summarize_records(
            'bug',
            [
                {'id': 1, 'assignedTo': 'alice'},
                {'id': 2, 'assignedTo': ''},
                {'id': 3},
                {'id': 4, 'assignedTo': 'closed'},
            ],
        )
        self.assertEqual({'alice': 1, 'unassigned': 3}, result['by_assignee'])

    def test_task_summary_marks_overdue_only_for_open_work(self) -> None:
        records = [
            {'id': 1, 'status': 'doing', 'deadline': '2026-08-24'},
            {'id': 2, 'status': 'done', 'deadline': '2026-08-20'},
            {'id': 3, 'status': 'wait', 'deadline': '2026-08-26'},
        ]
        result = mod.summarize_records('task', records, today='2026-08-25')
        self.assertEqual(1, result['deadline']['overdue'])
        self.assertEqual(1, result['deadline']['upcoming'])
        self.assertEqual(1, result['deadline']['completed_past_deadline'])

    def test_compare_keeps_each_scope_separate(self) -> None:
        result = mod.compare_summaries([
            {'scope': {'type': 'product', 'id': 1}, 'summary': {'total': 2}},
            {'scope': {'type': 'product', 'id': 2}, 'summary': {'total': 5}},
        ])
        self.assertEqual([2, 5], [item['summary']['total'] for item in result['comparisons']])


if __name__ == '__main__':
    unittest.main()
