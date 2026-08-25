from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'zentao_project_management.py'
spec = importlib.util.spec_from_file_location('zentao_project_management', MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class ProjectManagementTests(unittest.TestCase):
    def test_health_reports_fact_based_signals_without_numeric_score(self) -> None:
        resources = {
            'bug': [
                {'id': 1, 'status': 'active', 'severity': 1, 'pri': 1, 'assignedTo': 'alice'},
                {'id': 2, 'status': 'closed', 'severity': 2, 'assignedTo': 'bob'},
            ],
            'task': [
                {'id': 3, 'status': 'doing', 'deadline': '2026-08-24', 'assignedTo': 'alice'},
                {'id': 4, 'status': 'done', 'deadline': '2026-08-20', 'assignedTo': 'bob'},
            ],
            'story': [{'id': 5, 'status': 'active', 'assignedTo': ''}],
        }
        result = mod.build_health_report('execution', 9, resources, today='2026-08-25')
        self.assertNotIn('score', result)
        self.assertEqual('risk', result['status'])
        codes = {item['code'] for item in result['risk_signals']}
        self.assertIn('severity_1_bug', codes)
        self.assertIn('priority_1_bug', codes)
        self.assertIn('overdue_task', codes)
        self.assertIn('unassigned_work', codes)


    def test_non_work_resources_do_not_inflate_open_workload(self) -> None:
        resources = {
            'build': [{'id': 1, 'assignedTo': 'alice'}],
            'test-case': [{'id': 2, 'assignedTo': 'alice', 'status': 'normal'}],
            'task': [{'id': 3, 'assignedTo': 'alice', 'status': 'doing'}],
        }
        report = mod.build_health_report('execution', 1, resources, today='2026-08-25')
        self.assertEqual(1, report['workload']['alice']['open_items'])
        self.assertNotIn('open', report['resources']['build'])
        self.assertNotIn('open', report['resources']['test-case'])

    def test_health_is_unknown_when_every_query_failed(self) -> None:
        result = mod.build_health_report(
            'project', 7, {'bug': [], 'task': [], 'story': []},
            partial_failures=[{'resource': 'bug', 'message': 'unavailable'}],
        )
        self.assertEqual('unknown', result['status'])
        self.assertFalse(result['complete'])

    def test_workload_counts_open_items_by_assignee(self) -> None:
        resources = {
            'bug': [{'id': 1, 'status': 'active', 'assignedTo': 'alice'}],
            'task': [
                {'id': 2, 'status': 'doing', 'assignedTo': 'alice'},
                {'id': 3, 'status': 'done', 'assignedTo': 'bob'},
            ],
            'story': [{'id': 4, 'status': 'active', 'assignedTo': 'bob'}],
        }
        result = mod.build_workload(resources)
        self.assertEqual(2, result['alice']['open_items'])
        self.assertEqual(1, result['bob']['open_items'])


if __name__ == '__main__':
    unittest.main()
