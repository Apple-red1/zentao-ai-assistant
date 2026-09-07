from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
        with self.assertRaises(mod.AmbiguousMatchError) as raised:
            mod.resolve_user(users, '张三')
        self.assertEqual('user', raised.exception.kind)
        self.assertEqual('张三', raised.exception.value)
        self.assertEqual(['alice', 'alice2'], raised.exception.candidates)

    def test_main_preserves_user_ambiguous_error_output(self) -> None:
        users = [
            {'id': 1, 'account': 'alice', 'realname': '张三'},
            {'id': 2, 'account': 'alice2', 'realname': '张三'},
        ]

        class FakeClient:
            account = 'current'

            def list_all(self, resource: str, **kwargs: object) -> SimpleNamespace:
                if resource != 'user':
                    raise AssertionError(f'unexpected resource: {resource}')
                return SimpleNamespace(items=users, partial_failures=[])

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(mod, 'get_client', return_value=FakeClient()), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = mod.main(['overview', '--user', '张三', '--json'])

        self.assertEqual(1, code)
        self.assertEqual('', stdout.getvalue())
        self.assertEqual(
            {
                'error': {
                    'code': 'USER_AMBIGUOUS',
                    'message': '用户姓名存在歧义: alice, alice2',
                    'details': {'user': '张三', 'candidates': ['alice', 'alice2']},
                }
            },
            json.loads(stderr.getvalue()),
        )

    def test_main_preserves_user_not_found_error_output(self) -> None:
        class FakeClient:
            account = 'current'

            def list_all(self, resource: str, **kwargs: object) -> SimpleNamespace:
                if resource != 'user':
                    raise AssertionError(f'unexpected resource: {resource}')
                return SimpleNamespace(items=[], partial_failures=[])

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(mod, 'get_client', return_value=FakeClient()), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = mod.main(['overview', '--user', 'missing', '--json'])

        self.assertEqual(1, code)
        self.assertEqual('', stdout.getvalue())
        self.assertEqual(
            {
                'error': {
                    'code': 'PERSONAL_ERROR',
                    'message': '未找到用户: missing',
                    'details': {},
                }
            },
            json.loads(stderr.getvalue()),
        )

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

    def test_personal_bug_markdown_is_one_row_per_bug_with_stable_columns(self) -> None:
        resources = {
            'bug': [
                {'id': '2', 'title': '二号 | 标题', 'assignedTo': 'alice', 'status': 'resolved',
                 'pri': 2, 'severity': 3, 'resolvedBy': {'realname': '李四'},
                 'openedDate': '2026-09-03 10:00:00', 'resolvedDate': '2026-09-03 10:05:00'},
                {'id': 1, 'title': '一号', 'assignedTo': 'alice', 'status': 'active', 'pri': 1, 'severity': 1},
                {'id': 1, 'title': '一号', 'assignedTo': 'alice', 'status': 'active', 'pri': 1, 'severity': 1},
            ],
        }
        rendered = mod.render_personal_bugs(
            'alice', resources, complete=True, partial_failures=[],
            urls={1: 'http://localhost:8080/bug/1', 2: 'http://localhost:8080/bug/2'},
        )
        self.assertEqual(1, rendered.count('| [1]('))
        self.assertEqual(1, rendered.count('| [2]('))
        self.assertIn('| Bug ID | 标题 | 状态 | 优先级 | 严重程度 | 当前指派 | 解决人 | 创建时间 | 解决时间 |', rendered)
        self.assertIn('二号 \\| 标题', rendered)
        self.assertIn('李四', rendered)
        self.assertNotIn('- Bug：', rendered)

    def test_personal_bug_markdown_dedupes_equivalent_nested_values(self) -> None:
        resources = {
            'bug': [
                {'id': 8, 'title': '同一条', 'assignedTo': {'realname': 'Alice', 'account': 'alice'},
                 'status': 'active', 'pri': 1},
                {'id': '8', 'title': '同一条', 'assignedTo': {'account': 'alice', 'realname': 'Alice'},
                 'status': 'active', 'pri': '1', 'severity': 2},
            ],
        }
        rendered = mod.render_personal_bugs('alice', resources, complete=True,
                                             urls={8: 'http://localhost:8080/bug/8'})
        self.assertEqual(1, rendered.count('| [8]('))
        self.assertNotIn('BUG_SNAPSHOT_CONFLICT', rendered)
        self.assertIn('| P1 | S2 |', rendered)

    def test_personal_markdown_keeps_partial_failure_after_table(self) -> None:
        resources = {'bug': [{'id': 3, 'title': '部分结果', 'assignedTo': 'alice', 'status': 'active'}]}
        rendered = mod.render_personal_bugs(
            'alice', resources, complete=False,
            partial_failures=[{'code': 'PAGE_READ_FAILED', 'page': 2}],
        )
        self.assertLess(rendered.index('| Bug ID |'), rendered.index('## 数据完整性'))
        self.assertIn('PAGE_READ_FAILED', rendered)

    def test_personal_markdown_has_fixed_table_for_zero_and_reports_link_failure(self) -> None:
        empty = mod.render_personal_bugs('alice', {'bug': []}, complete=True, urls={})
        self.assertIn('| Bug ID | 标题 | 状态 | 优先级 | 严重程度 | 当前指派 | 解决人 | 创建时间 | 解决时间 |', empty)
        self.assertIn('查询到 0 条 Bug。', empty)
        self.assertIn('没有 Bug。', empty)

        missing_link = mod.render_personal_bugs(
            'alice',
            {'bug': [{'id': 4, 'title': '无链接', 'assignedTo': 'alice', 'status': 'active'}]},
            complete=True,
            urls={},
        )
        self.assertIn('| 4（链接生成失败） |', missing_link)
        self.assertIn('## 链接生成', missing_link)

    def test_personal_cli_markdown_uses_url_mapping_and_json_stays_machine_readable(self) -> None:
        resources = {
            'bug': [{'id': 9, 'title': '一个 Bug', 'assignedTo': 'alice', 'status': 'active', 'pri': 1, 'severity': 2}],
            'task': [], 'story': [], 'requirement': [], 'ticket': [], 'feedback': [],
        }

        class FakeClient:
            account = 'alice'

            def bug_web_urls(self, ids: list[int]) -> list[dict[str, object]]:
                return [{'id': ident, 'url': f'http://localhost:8080/index.php?bugID={ident}'} for ident in ids]

        with patch.object(mod, 'get_client', return_value=FakeClient()), patch.object(mod, '_collect', return_value=(resources, [])):
            markdown = io.StringIO()
            with contextlib.redirect_stdout(markdown):
                code = mod.main(['worklist', '--markdown'])
            self.assertEqual(0, code)
            self.assertIn('| [9](http://localhost:8080/index.php?bugID=9) |', markdown.getvalue())
            self.assertEqual(1, markdown.getvalue().count('| [9]('))

            machine = io.StringIO()
            with contextlib.redirect_stdout(machine):
                code = mod.main(['worklist', '--json'])
            self.assertEqual(0, code)
            payload = json.loads(machine.getvalue())
            self.assertEqual(['bug'], [item['resource'] for item in payload['items']])
            self.assertNotIn('| Bug ID |', machine.getvalue())


if __name__ == '__main__':
    unittest.main()
