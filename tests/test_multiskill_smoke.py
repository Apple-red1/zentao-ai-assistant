from __future__ import annotations

import json
import os
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
