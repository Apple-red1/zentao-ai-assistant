from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'zentao_personal.py'
spec = importlib.util.spec_from_file_location('zentao_personal', MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class PersonalTests(unittest.TestCase):
    def test_resolve_user_rejects_duplicate_realname(self) -> None:
        users = [
            {'id': 1, 'account': 'alice', 'realname': '张三'},
            {'id': 2, 'account': 'alice2', 'realname': '张三'},
        ]
        with self.assertRaises(mod.UserAmbiguousError) as raised:
            mod.resolve_user(users, '张三')
        self.assertEqual(['alice', 'alice2'], raised.exception.candidates)

    def test_personal_overview_filters_assignee_and_builds_risk_buckets(self) -> None:
        resources = {
            'bug': [
                {'id': 1, 'title': 'critical', 'assignedTo': 'alice', 'status': 'active', 'pri': 1, 'severity': 1},
                {'id': 2, 'title': 'other', 'assignedTo': 'bob', 'status': 'active', 'pri': 1},
            ],
            'task': [
                {'id': 3, 'name': 'late task', 'assignedTo': 'alice', 'status': 'doing', 'deadline': '2026-08-24', 'pri': 2},
                {'id': 4, 'name': 'done', 'assignedTo': 'alice', 'status': 'done', 'deadline': '2026-08-20'},
            ],
        }
        result = mod.build_personal_overview('alice', resources, today='2026-08-25')
        self.assertEqual(1, result['resources']['bug']['total'])
        self.assertEqual(2, result['resources']['task']['total'])
        self.assertEqual(1, len(result['risks']['severity_1_bugs']))
        self.assertEqual(1, len(result['risks']['priority_1_bugs']))
        self.assertEqual({'resource', 'id', 'title', 'status', 'priority', 'severity'}, set(result['risks']['severity_1_bugs'][0]))
        self.assertEqual(1, len(result['risks']['overdue_tasks']))
        self.assertEqual(3, result['total_items'])

    def test_worklist_deadline_ranking_is_task_specific(self) -> None:
        resources = {
            'story': [{'id': 1, 'title': 'story', 'assignedTo': 'alice', 'status': 'active', 'end': '2026-08-01'}],
            'task': [{'id': 2, 'name': 'task', 'assignedTo': 'alice', 'status': 'doing', 'deadline': '2026-08-24'}],
        }
        items = mod.build_worklist('alice', resources, today='2026-08-25')
        self.assertEqual(2, items[0]['id'])
        story = next(item for item in items if item['resource'] == 'story')
        self.assertIsNone(story['deadline_state'])


if __name__ == '__main__':
    unittest.main()
