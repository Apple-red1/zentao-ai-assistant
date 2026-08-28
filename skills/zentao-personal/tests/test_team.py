from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'zentao_personal.py'
spec = importlib.util.spec_from_file_location('personal_team_entry', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from zentao.runtime import ZentaoClient
from team_config import TeamError, TeamStore
from team_presenter import render_team_report


def bug(ident, account='alice', status='active', **kwargs):
    return dict(id=ident, assignedTo=account, status=status, title=f'Bug {ident}',
                pri=2, severity=2, openedDate='2026-08-01 10:00:00') | kwargs


class TeamTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('pathlib.Path.home', return_value=self.home))
        self.config = SimpleNamespace(base_url='http://localhost:8080/zentao/', account='me')
        self.client = ZentaoClient(services=SimpleNamespace(session=SimpleNamespace(config=self.config)))
        self.enterContext(patch.object(mod, 'get_client', return_value=self.client))
        self.users = [{'id': 1, 'account': 'me', 'realname': '本人'},
                      {'id': 2, 'account': 'alice', 'realname': '张三'},
                      {'id': 3, 'account': 'bob', 'realname': '李四'}]
        self.rows = [bug(1, 'me'), bug(2), bug(3, status='resolved'), bug(4, 'bob', 'closed')]
        self.calls = []
        self.fault = None
        self.enterContext(patch.object(self.client, 'list_page', side_effect=self.page))

    def page(self, resource, *, scope=None, scope_id=None, page=1, per_page=1000, browse=None):
        self.calls.append((resource, scope, scope_id, page, browse))
        if self.fault:
            self.fault(resource, scope, scope_id, page, browse)
        rows = self.users if resource == 'user' else self.rows if resource == 'bug' else [{'id': 1}]
        keys = {'user': 'users', 'bug': 'bugs', 'product': 'products', 'project': 'projects', 'execution': 'executions'}
        start = (page - 1) * per_page
        return {keys[resource]: rows[start:start + per_page], 'pager': {'total': len(rows)}}

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mod.main([*args, '--json'])
        return code, json.loads(out.getvalue() or err.getvalue())

    def ok(self, *args):
        code, data = self.run_cli(*args)
        self.assertEqual(0, code, data)
        return data

    def configure(self):
        return self.ok('team-add', '--member', '张三', '--member', 'bob', '--member', 'me')

    def test_empty_team_includes_self_without_writing_config(self):
        result = self.ok('team-view')
        self.assertEqual([], result['configured_accounts'])
        self.assertEqual(['me'], result['effective_accounts'])
        self.assertEqual([], list(self.home.rglob('*.json')))

    def test_add_remove_replace_clear_dedupe_and_protect_self(self):
        self.assertEqual(['alice', 'bob'], self.configure()['configured_accounts'])
        self.assertEqual(['alice', 'bob'], self.ok('team-add', '--member', 'alice')['configured_accounts'])
        self.assertEqual(['me', 'alice'], self.ok('team-remove', '--member', 'bob', '--member', 'me')['effective_accounts'])
        self.assertEqual(['bob'], self.ok('team-replace', '--member', 'bob')['configured_accounts'])
        self.assertEqual(['me'], self.ok('team-replace', '--clear')['effective_accounts'])

    def test_storage_is_user_owned_private_and_isolated(self):
        self.configure()
        paths = list((self.home / '.zentao-ai-assistant' / 'teams').glob('*.json'))
        self.assertEqual(1, len(paths))
        body = json.loads(paths[0].read_text())
        self.assertEqual(['alice', 'bob'], body['members'])
        self.assertNotIn('password', paths[0].read_text().lower())
        if os.name == 'posix':
            self.assertEqual(0o600, stat.S_IMODE(paths[0].stat().st_mode))
            self.assertEqual(0o700, stat.S_IMODE(paths[0].parent.stat().st_mode))
        self.config.base_url = 'HTTP://LOCALHOST:8080/zentao'
        self.assertEqual(['alice', 'bob'], self.ok('team-view')['configured_accounts'])
        self.config.account = 'alice'
        self.assertEqual([], self.ok('team-view')['configured_accounts'])
        self.config.account = 'me'
        self.config.base_url = 'http://localhost:8081/zentao'
        self.assertEqual([], self.ok('team-view')['configured_accounts'])

    def test_ambiguous_missing_and_incomplete_directory_never_change_config(self):
        self.configure()
        paths = list(self.home.rglob('*.json'))
        before = paths[0].read_bytes()
        self.users.append({'id': 4, 'account': 'alice2', 'realname': '张三'})
        code, data = self.run_cli('team-replace', '--member', '张三')
        self.assertEqual(1, code)
        self.assertEqual('USER_AMBIGUOUS', data['error']['code'])
        code, _ = self.run_cli('team-add', '--member', 'missing')
        self.assertEqual(1, code)
        self.fault = lambda r, s, i, p, b: (_ for _ in ()).throw(RuntimeError('directory denied')) if r == 'user' and b == 'outside' else None
        code, data = self.run_cli('team-replace', '--clear')
        self.assertEqual(1, code)
        self.assertEqual('TEAM_DIRECTORY_INCOMPLETE', data['error']['code'])
        self.assertEqual(before, paths[0].read_bytes())

    def test_queries_share_all_ids_counts_groups_and_zero_members(self):
        self.configure()
        bugs = self.ok('team-bugs', '--per-page', '1')
        brief = self.ok('team-brief', '--per-page', '1')
        self.assertEqual(bugs, brief)
        self.assertTrue(bugs['complete'])
        self.assertEqual([1, 2, 3], bugs['bug_ids'])
        self.assertEqual({'total_not_closed': 3, 'active_immediate_action': 2, 'resolved_awaiting_verification': 1}, bugs['summary'])
        self.assertEqual(['me', 'alice', 'bob'], [m['account'] for m in bugs['active']])
        self.assertEqual([], bugs['active'][2]['bugs'])
        self.assertTrue(bugs['active'][2]['complete'])
        self.assertEqual([3], [b['id'] for b in bugs['awaiting_verification'][1]['bugs']])
        self.assertTrue(all(c[4] == 'all' for c in self.calls if c[0] == 'bug'))
        self.assertTrue(any(c[3] == 4 for c in self.calls if c[0] == 'bug'))

    def test_explicit_scopes_do_not_scan_global_or_change_team(self):
        self.configure()
        for scope in ('product', 'project', 'execution'):
            self.calls.clear()
            result = self.ok('team-bugs', '--' + scope, '7')
            self.assertEqual({'type': scope, 'id': 7}, result['scope'])
            self.assertEqual([('bug', scope, 7, 1, 'all')], [c for c in self.calls if c[0] != 'user'])
        self.assertEqual(['alice', 'bob'], self.ok('team-view')['configured_accounts'])

    def test_failed_second_page_keeps_first_page_and_never_claims_zero(self):
        self.configure()
        self.fault = lambda r, s, i, p, b: (_ for _ in ()).throw(RuntimeError('page denied')) if r == 'bug' and p == 2 else None
        result = self.ok('team-bugs', '--product', '1', '--per-page', '1')
        self.assertFalse(result['complete'])
        self.assertEqual([1], result['bug_ids'])
        self.assertTrue(result['partial_failures'])
        self.assertTrue(all(not m['complete'] for m in result['active']))
        self.assertEqual(result, self.ok('team-brief', '--product', '1', '--per-page', '1'))

    def test_known_accounts_only_unknown_status_and_bad_dates_are_partial(self):
        self.configure()
        self.rows = [bug(1, 'me'), bug(2, status='mystery'), bug(3, assignedTo={'realname': 'alice'}),
                     bug(4, assignedTo='closed'), bug(5, assignedTo=''), bug(6, openedDate='bad')]
        result = self.ok('team-bugs', '--product', '1')
        self.assertEqual([1, 6], result['bug_ids'])
        self.assertFalse(result['complete'])
        codes = {f['code'] for f in result['partial_failures']}
        self.assertIn('BUG_STATUS_INVALID', codes)
        self.assertIn('BUG_ASSIGNEE_INVALID', codes)
        self.assertIn('BUG_DATE_INVALID', codes)

    def test_stable_sort_priority_severity_oldest_then_numeric_id(self):
        self.configure()
        self.rows = [bug(10), bug(2), bug(3, pri=1, severity=3), bug(4, pri=1, severity=1),
                     bug(5, pri=1, severity=1, openedDate='2026-07-01'), bug(6, pri=None),
                     bug(7, pri=1, severity=None)]
        result = self.ok('team-bugs', '--product', '1')
        self.assertEqual([5, 4, 3, 2, 10, 7, 6], [b['id'] for b in result['active'][1]['bugs']])
        self.assertIsNone(result['active'][1]['bugs'][-1]['pri'])

    def test_member_disappears_keeps_other_members_and_marks_missing_member(self):
        self.configure()
        self.users = [u for u in self.users if u['account'] != 'bob']
        result = self.ok('team-bugs', '--product', '1')
        self.assertEqual([1, 2, 3], result['bug_ids'])
        self.assertFalse(result['complete'])
        self.assertFalse(result['active'][2]['complete'])
        self.assertTrue(result['active'][0]['complete'])

    def test_directory_duplicate_account_conflict_blocks_even_exact_name(self):
        self.users.append({'id': 20, 'account': 'alice', 'realname': '另一个人'})
        code, data = self.run_cli('team-add', '--member', 'alice')
        self.assertEqual(1, code)
        self.assertEqual('TEAM_DIRECTORY_INCOMPLETE', data['error']['code'])
        self.assertFalse(list(self.home.rglob('*.json')))

    def test_scope_failure_continues_other_surfaces_and_retains_partial_rows(self):
        self.configure()
        self.fault = lambda r, s, i, p, b: (_ for _ in ()).throw(RuntimeError('permission denied')) if r == 'product' else None
        result = self.ok('team-bugs')
        self.assertFalse(result['complete'])
        self.assertEqual([1, 2, 3], result['bug_ids'])
        self.assertTrue(any(c[1] == 'execution' for c in self.calls if c[0] == 'bug'))

    def test_conflicting_duplicate_ids_are_not_arbitrarily_assigned(self):
        self.configure()
        self.rows = [bug(1), bug('1', 'bob', 'resolved'), bug(2), bug('2')]
        result = self.ok('team-bugs', '--product', '1')
        self.assertEqual([2], result['bug_ids'])
        self.assertFalse(result['complete'])
        self.assertEqual(2, result['duplicates_removed'])
        self.assertIn('BUG_SNAPSHOT_CONFLICT', [f['code'] for f in result['partial_failures']])

    def test_invalid_id_unknown_status_and_owner_alias_conflict_are_retained_as_failures(self):
        self.configure()
        self.rows = [bug(None), bug(True), bug(2, status=None), bug(3, assignedToAccount='bob'),
                     bug(4, assignedTo={'realname': '张三'}, assignedToAccount='alice')]
        result = self.ok('team-bugs', '--product', '1')
        self.assertEqual([4], result['bug_ids'])
        self.assertFalse(result['complete'])
        self.assertEqual({'BUG_ID_INVALID', 'BUG_STATUS_INVALID', 'BUG_ASSIGNEE_INVALID'},
                         {f['code'] for f in result['partial_failures']})

    def test_mixed_timezone_dates_use_numeric_id_fallback_with_warning(self):
        self.configure()
        self.rows = [bug(3, openedDate='2026-07-01T01:00:00Z'), bug(2, openedDate='2026-08-01 01:00:00')]
        result = self.ok('team-bugs', '--product', '1')
        self.assertEqual([2, 3], [b['id'] for b in result['active'][1]['bugs']])
        self.assertFalse(result['complete'])
        self.assertIn('BUG_DATE_INCOMPARABLE', [f['code'] for f in result['partial_failures']])

    def test_aware_dates_compare_same_instants_and_unknown_levels_stay_last(self):
        self.configure()
        self.rows = [bug(2, openedDate='2026-08-01T09:00:00+08:00'),
                     bug(1, openedDate='2026-08-01T02:00:00Z'), bug(3, pri='unknown')]
        result = self.ok('team-bugs', '--product', '1')
        self.assertEqual([2, 1, 3], [b['id'] for b in result['active'][1]['bugs']])
        self.assertTrue(result['complete'])

    def test_empty_bug_collection_has_every_member_in_both_phases(self):
        self.configure()
        self.rows = []
        result = self.ok('team-bugs')
        self.assertTrue(result['complete'])
        self.assertEqual([], result['bug_ids'])
        self.assertEqual(0, result['summary']['total_not_closed'])
        self.assertEqual(3, len(result['active']))
        self.assertEqual(3, len(result['awaiting_verification']))

    def test_malformed_status_and_out_of_range_date_do_not_abort_other_bugs(self):
        self.configure()
        self.rows = [bug(1, status=['active']), bug(2, openedDate='9999-12-31T23:59:59-23:59'), bug(3)]
        result = self.ok('team-bugs', '--product', '1')
        self.assertEqual([2, 3], result['bug_ids'])
        self.assertFalse(result['complete'])
        self.assertIn('BUG_DATE_INVALID', [f['code'] for f in result['partial_failures']])

    def test_repeated_page_stalls_instead_of_proclaiming_completeness(self):
        self.configure()
        original = self.page
        def repeated(resource, **kwargs):
            if resource == 'bug':
                return {'bugs': [bug(1)], 'pager': {'total': 2}}
            return original(resource, **kwargs)
        with patch.object(self.client, 'list_page', side_effect=repeated):
            result = self.ok('team-bugs', '--product', '1', '--per-page', '1')
        self.assertFalse(result['complete'])
        self.assertEqual([1], result['bug_ids'])
        self.assertIn('PAGINATION_STALLED', [f['code'] for f in result['partial_failures']])

    def test_bad_arguments_cannot_read_or_change_data(self):
        for args in [('team-replace',), ('team-replace', '--clear', '--member', 'bob'),
                     ('team-bugs', '--user', 'alice'), ('team-bugs', '--per-page', '0'),
                     ('team-bugs', '--product', '-1'), ('team-bugs', '--product', '1', '--project', '2'),
                     ('overview', '--member', 'alice'), ('team-view', '--cache-data')]:
            with self.subTest(args=args), self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                mod.main(list(args))
        self.assertEqual([], self.calls)
        self.assertFalse(list(self.home.rglob('*.json')))

    def test_private_store_blocks_corruption_symlinks_and_unknown_schema(self):
        self.configure()
        store = TeamStore(self.client.connection_identity)
        original = store.path.read_bytes()
        for content in ('not json', '{"schema_version":99}', '{"members":"alice"}'):
            store.path.write_text(content)
            with self.assertRaises(TeamError):
                store.update('replace', [])
            self.assertEqual(content, store.path.read_text())
        store.path.write_bytes(original)
        target = self.home / 'outside.json'
        target.write_bytes(original)
        store.path.unlink()
        store.path.symlink_to(target)
        with self.assertRaises(TeamError):
            store.read()
        with self.assertRaises(TeamError):
            store.update('replace', [])
        self.assertEqual(original, target.read_bytes())

    def test_parent_symlink_is_rejected_without_touching_target(self):
        target = self.home / 'outside'
        target.mkdir()
        (self.home / '.zentao-ai-assistant').symlink_to(target, target_is_directory=True)
        store = TeamStore(self.client.connection_identity)
        with self.assertRaises(TeamError):
            store.update('replace', ['alice'])
        self.assertEqual([], list(target.iterdir()))

    def test_atomic_write_failure_and_concurrent_writer_do_not_lose_old_data(self):
        self.configure()
        store = TeamStore(self.client.connection_identity)
        old = store.path.read_bytes()
        with patch('team_config.os.replace', side_effect=OSError('disk failed')):
            with self.assertRaises(OSError):
                store.update('replace', [])
        self.assertEqual(old, store.path.read_bytes())
        self.assertEqual([store.path], list(store.directory.iterdir()))
        lock = store.path.with_suffix('.lock')
        lock.mkdir()
        with self.assertRaises(TeamError) as raised:
            store.update('add', ['other'])
        self.assertEqual('TEAM_CONFIG_BUSY', raised.exception.code)
        self.assertEqual(old, store.path.read_bytes())

    def test_markdown_same_tables_link_by_id_escape_content_and_distinguish_zero(self):
        self.configure()
        self.rows[1]['title'] = 'A | [B] <tag>\nC'
        report = self.ok('team-bugs', '--product', '1')
        response = SimpleNamespace(returncode=0, stdout=json.dumps([
            {'id': i, 'url': f'http://localhost/index.php?bugID={i}'} for i in reversed(report['bug_ids'])]))
        with patch('team_presenter.subprocess.run', return_value=response) as run:
            detail = render_team_report(report)
            brief = render_team_report(report, brief=True)
        self.assertEqual(detail, brief[brief.index('## 一、'):])
        self.assertIn('| [2](http://localhost/index.php?bugID=2) | A \\| \\[B\\] &lt;tag&gt;<br>C | P2 | 激活 |', detail)
        self.assertIn('### 李四（0）', detail)
        self.assertIn('| Bug ID | 标题 | 优先级 | 状态 |', detail)
        self.assertNotIn('| 负责人 |', detail)
        self.assertEqual(['bug', 'web-url', '1', '2', '3', '--json'], run.call_args.args[0][2:])
        report['complete'] = False
        report['active'][2]['complete'] = False
        with patch('team_presenter.subprocess.run', return_value=response):
            partial = render_team_report(report, brief=True)
        self.assertIn('### 李四（数据不完整）', partial)
        self.assertIn('已获取 3 个未关闭 Bug', partial)

    def test_markdown_link_failure_preserves_every_row_without_guessing(self):
        self.configure()
        report = self.ok('team-bugs', '--product', '1')
        with patch('team_presenter.subprocess.run', side_effect=OSError('unavailable')):
            text = render_team_report(report)
        for ident in report['bug_ids']:
            self.assertIn(f'| {ident}（链接生成失败） |', text)
        self.assertIn('未猜测 URL', text)
        self.assertTrue(report['complete'])


if __name__ == '__main__':
    unittest.main()
