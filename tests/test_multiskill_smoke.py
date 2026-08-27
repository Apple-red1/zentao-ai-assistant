from __future__ import annotations

import json
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZENTAO_ROOT = ROOT / 'skills' / 'zentao'
if str(ZENTAO_ROOT) not in sys.path:
    sys.path.insert(0, str(ZENTAO_ROOT))

from tests.fake_zentao.server import FakeZenTao


def env_for(base_url: str, *, cache_dir: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.update({'ZENTAO_BASE_URL': base_url, 'ZENTAO_ACCOUNT': 'admin', 'ZENTAO_PASSWORD': 'secret'})
    if cache_dir:
        env['ZENTAO_TOKEN_CACHE_DIR'] = cache_dir
        env.pop('ZENTAO_TOKEN_CACHE_DISABLED', None)
    else:
        env['ZENTAO_TOKEN_CACHE_DISABLED'] = '1'
    return env


class HumanAttestedCLIExamplesTests(unittest.TestCase):
    """Execute the published commands, not a second implementation of Agent routing."""

    def setUp(self) -> None:
        self.fake = self.enterContext(FakeZenTao())
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        skill = ROOT / 'skills' / 'zentao-bug-resolver'
        workflow = (skill / 'references' / 'workflow.md').read_text(encoding='utf-8')
        human = workflow.split('## 0. HUMAN_ATTESTED_RESOLVE', 1)[1].split('## 1. 执行面', 1)[0]
        self.commands = [shlex.split(block.replace('\\\n', '')) for block in re.findall(r'```bash\n(.*?)\n```', human, re.S)]
        self.assertEqual(['view', 'resolve', 'view'], [cmd[3] for cmd in self.commands])
        templates = (skill / 'references' / 'comment-templates.md').read_text(encoding='utf-8')
        human_template = templates.split('## Human-attested', 1)[1].split('## Fixed', 1)[0]
        self.comment = re.search(r'```text\n(.*?)\n```', human_template, re.S).group(1).replace('<id>', '1')
        self.comment_file = self.directory / 'human attested.txt'
        self.comment_file.write_text(self.comment, encoding='utf-8')

    def command(self, index: int, *, build: str | None = None) -> subprocess.CompletedProcess[str]:
        argv = [str(self.comment_file) if token == '<generated-human-attested-comment.txt>' else '1' if token == '<id>' else token for token in self.commands[index]]
        if build is not None:
            argv[argv.index('--resolved-build') + 1] = build
        return subprocess.run([sys.executable, *argv[1:]], cwd=ROOT, env=env_for(self.fake.base_url), text=True, capture_output=True, timeout=20)

    def business_requests(self) -> list[dict]:
        return [r for r in self.fake.state.requests if r['endpoint_id'] != 'token.login']

    def test_default_example_sends_only_fixed_trunk_and_utf8_comment_then_explicit_readback(self) -> None:
        before = self.command(0)
        self.assertEqual(0, before.returncode, before.stderr)
        self.assertEqual('active', json.loads(before.stdout)['status'])
        write = self.command(1)
        self.assertEqual(0, write.returncode, write.stderr)
        self.assertEqual(['bug.view', 'bug.resolve'], [r['endpoint_id'] for r in self.business_requests()])
        self.assertEqual({'resolution': 'fixed', 'resolvedBuild': 'trunk', 'comment': self.comment}, self.business_requests()[-1]['body'])
        after = self.command(2)
        self.assertEqual(0, after.returncode, after.stderr)
        self.assertEqual('resolved', json.loads(after.stdout)['status'])
        self.assertEqual(['GET', 'PUT', 'GET'], [r['method'] for r in self.business_requests()])

    def test_explicit_build_and_user_explanation_are_preserved(self) -> None:
        comment = self.comment.replace('本次解决版本参数默认使用主干（trunk）。', '本次解决版本参数按用户指定使用 7。') + '\n用户说明：修正空列表判断。'
        self.comment_file.write_text(comment, encoding='utf-8')
        self.assertEqual(0, self.command(0).returncode)
        write = self.command(1, build='7')
        self.assertEqual(0, write.returncode, write.stderr)
        self.assertEqual({'resolution': 'fixed', 'resolvedBuild': 7, 'comment': comment}, self.business_requests()[-1]['body'])
        after = self.command(2)
        self.assertEqual('resolved', json.loads(after.stdout)['status'])

    def test_rejected_trunk_or_permission_reports_real_error_without_implicit_retry(self) -> None:
        original_handle = self.fake.state.handle

        def reject_build(route, path_params, query, body):
            if route.endpoint_id == 'bug.resolve':
                return 200, {'status': 'fail', 'message': {'resolvedBuild': ['trunk is not allowed']}}
            return original_handle(route, path_params, query, body)

        for fault in ('build', '403'):
            with self.subTest(fault=fault):
                self.fake.state.reset()
                self.fake.state.handle = reject_build if fault == 'build' else original_handle
                if fault == '403':
                    self.fake.state.plan_faults('bug.resolve', '403')
                self.assertEqual(0, self.command(0).returncode)
                write = self.command(1)
                self.assertEqual(1, write.returncode)
                self.assertEqual('', write.stdout)
                error = json.loads(write.stderr)['error']
                self.assertTrue(error['code'])
                self.assertIn('trunk is not allowed' if fault == 'build' else '403', write.stderr)
                self.assertEqual(['bug.view', 'bug.resolve'], [r['endpoint_id'] for r in self.business_requests()])
                self.assertEqual('active', json.loads(self.command(2).stdout)['status'])

    def test_unknown_write_has_no_implicit_retry_or_readback(self) -> None:
        for fault, status in (('drop', 'active'), ('commit_then_drop', 'resolved')):
            with self.subTest(fault=fault):
                self.fake.state.reset()
                self.fake.state.plan_faults('bug.resolve', fault)
                self.assertEqual(0, self.command(0).returncode)
                write = self.command(1)
                self.assertEqual(1, write.returncode)
                self.assertEqual('UNKNOWN_WRITE_RESULT', json.loads(write.stderr)['error']['code'])
                self.assertEqual(['bug.view', 'bug.resolve'], [r['endpoint_id'] for r in self.business_requests()])
                after = self.command(2)
                self.assertEqual(status, json.loads(after.stdout)['status'])
                self.assertEqual(['bug.view', 'bug.resolve', 'bug.view'], [r['endpoint_id'] for r in self.business_requests()])


class MultiSkillSmokeTests(unittest.TestCase):
    def test_statistics_personal_and_project_scripts_run_against_fake(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources['bug']['1'].update({'assignedTo': 'admin', 'severity': 1, 'pri': 1})
            fake.state.resources['task']['1'].update({'assignedTo': 'admin', 'deadline': '2026-08-24', 'status': 'doing'})
            commands = [
                ['skills/zentao-statistics/scripts/zentao_statistics.py', 'summary', 'bug', '--product', '1', '--json'],
                ['skills/zentao-personal/scripts/zentao_personal.py', 'overview', '--today', '2026-08-25', '--json'],
                ['skills/zentao-project-management/scripts/zentao_project_management.py', 'health', '--execution', '1', '--today', '2026-08-25', '--json'],
            ]
            outputs = []
            for command in commands:
                result = subprocess.run([sys.executable, *command], cwd=ROOT, env=env_for(fake.base_url), text=True, capture_output=True, timeout=20)
                self.assertEqual(0, result.returncode, f"{command}\n{result.stderr}")
                outputs.append(json.loads(result.stdout))
            self.assertEqual(1, outputs[0]['total'])
            self.assertGreaterEqual(outputs[1]['total_items'], 2)
            self.assertEqual('risk', outputs[2]['status'])

    def test_bug_resolver_read_commands_run_in_subprocess_and_stay_read_only(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            env = env_for(fake.base_url)
            script = 'skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py'

            select = subprocess.run(
                [sys.executable, script, 'select', '--product', '1', '--json'],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=20,
            )
            self.assertEqual(0, select.returncode, select.stderr)
            self.assertEqual(1, json.loads(select.stdout)['current_bug_id'])

            snapshot = subprocess.run(
                [sys.executable, script, 'snapshot', '--bug-id', '1', '--json'],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=20,
            )
            self.assertEqual(0, snapshot.returncode, snapshot.stderr)
            snapshot_payload = json.loads(snapshot.stdout)
            self.assertEqual(1, snapshot_payload['bug_id'])

            baseline = Path(td) / 'snapshot.json'
            baseline.write_text(snapshot.stdout, encoding='utf-8')
            compare = subprocess.run(
                [sys.executable, script, 'compare', '--bug-id', '1', '--baseline-file', str(baseline), '--json'],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=20,
            )
            self.assertEqual(0, compare.returncode, compare.stderr)
            compare_payload = json.loads(compare.stdout)
            self.assertTrue(compare_payload['changed'])
            self.assertTrue(compare_payload['comparison_blocked'])
            self.assertEqual('CRITICAL_FIELD_UNAVAILABLE', compare_payload['block_reason'])
            self.assertEqual([], compare_payload['changes'])

            business_requests = [request for request in fake.state.requests if request['endpoint_id'] != 'token.login']
            self.assertTrue(business_requests)
            self.assertTrue(all(request['method'] == 'GET' for request in business_requests))
            self.assertFalse(any(request['endpoint_id'] == 'bug.resolve' for request in fake.state.requests))


    def test_statistics_cache_data_is_private_and_under_project_tmp(self) -> None:
        with FakeZenTao() as fake:
            result = subprocess.run(
                [sys.executable, 'skills/zentao-statistics/scripts/zentao_statistics.py', 'summary', 'bug', '--product', '1', '--cache-data', '--json'],
                cwd=ROOT, env=env_for(fake.base_url), text=True, capture_output=True, timeout=20,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            path = Path(json.loads(result.stdout)['temp_data'])
            try:
                self.assertTrue(path.is_file())
                self.assertTrue(path.resolve().is_relative_to((ROOT / '.tmp' / 'zentao' / 'statistics').resolve()))
                if os.name == 'posix':
                    self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
                    self.assertEqual(0o700, stat.S_IMODE(path.parent.stat().st_mode))
            finally:
                import shutil
                shutil.rmtree(path.parent, ignore_errors=True)

    def test_token_cache_reuses_login_across_cli_processes(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            env = env_for(fake.base_url, cache_dir=td)
            for _ in range(2):
                result = subprocess.run([sys.executable, 'skills/zentao/scripts/zentao.py', 'doctor', '--json'], cwd=ROOT, env=env, text=True, capture_output=True, timeout=10)
                self.assertEqual(0, result.returncode, result.stderr)
            logins = [item for item in fake.state.requests if item['endpoint_id'] == 'token.login']
            self.assertEqual(1, len(logins))
            cache_files = list(Path(td).glob('token-*.json'))
            self.assertEqual(1, len(cache_files))
            self.assertNotIn('secret', cache_files[0].read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
