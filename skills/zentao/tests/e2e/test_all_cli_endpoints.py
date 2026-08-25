
from __future__ import annotations

import json
import unittest
from collections import Counter

from ..fake_zentao.server import FakeZenTao
from ..support import CATALOG, SAMPLES, run_cli, run_cli_batch
from zentao_skill.cli.main import CLI_ENDPOINT_IDS

E2E_ENDPOINT_IDS = frozenset(item["endpoint_id"] for item in CATALOG)


class CliE2ETests(unittest.TestCase):
    def test_cli_surface_declares_all_120_endpoints(self) -> None:
        self.assertEqual(E2E_ENDPOINT_IDS, CLI_ENDPOINT_IDS)

    def test_all_120_endpoints_are_reachable_through_cli_or_auth_bootstrap(self) -> None:
        cases=[{"endpoint_id": item["endpoint_id"], "argv": SAMPLES[item["endpoint_id"]]["cli_argv"]} for item in CATALOG]
        with FakeZenTao() as fake:
            result=run_cli_batch(fake.base_url,cases)
            self.assertEqual(0,result.returncode,msg=result.stderr)
            outcomes=json.loads(result.stdout)
            self.assertEqual(120,len(outcomes))
            for outcome in outcomes:
                endpoint_id=outcome["endpoint_id"]
                with self.subTest(endpoint=endpoint_id):
                    self.assertEqual(0,outcome["returncode"],msg=f"{endpoint_id}\nstdout={outcome['stdout']}\nstderr={outcome['stderr']}")
                    self.assertTrue(outcome["stdout"].strip())
                    json.loads(outcome["stdout"])
            business_counts=Counter(r["endpoint_id"] for r in fake.state.requests if r["endpoint_id"] != "token.login")
            for item in CATALOG:
                if item["endpoint_id"] != "token.login":
                    self.assertEqual(1,business_counts[item["endpoint_id"]],item["endpoint_id"])
            self.assertGreaterEqual(sum(1 for r in fake.state.requests if r["endpoint_id"]=="token.login"),1)

    def test_all_delete_commands_require_yes_before_any_http(self) -> None:
        delete_items=[item for item in CATALOG if item["risk_class"]=="R3"]
        cases=[{"endpoint_id": item["endpoint_id"], "argv": [x for x in SAMPLES[item["endpoint_id"]]["cli_argv"] if x!="--yes"]} for item in delete_items]
        with FakeZenTao() as fake:
            result=run_cli_batch(fake.base_url,cases)
            self.assertEqual(0,result.returncode,result.stderr)
            outcomes=json.loads(result.stdout)
            self.assertEqual(len(delete_items),len(outcomes))
            for outcome in outcomes:
                self.assertEqual(2,outcome["returncode"],outcome["endpoint_id"])
                self.assertEqual("",outcome["stdout"])
                self.assertEqual("USAGE_ERROR",json.loads(outcome["stderr"])["error"]["code"])
            self.assertEqual([],fake.state.requests)


if __name__ == "__main__": unittest.main()
