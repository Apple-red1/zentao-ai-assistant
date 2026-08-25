
from __future__ import annotations

import json
import unittest
from concurrent.futures import ThreadPoolExecutor

from ..fake_zentao.server import FakeZenTao
from ..support import run_cli


class SkillScenarioTests(unittest.TestCase):
    def test_product_crud_lifecycle_uses_explicit_commands(self) -> None:
        with FakeZenTao() as fake:
            created=run_cli(fake.base_url,["product","create","--name","scenario-product","--json"])
            self.assertEqual(0,created.returncode,created.stderr)
            ident=json.loads(created.stdout)["id"]
            self.assertEqual(0,run_cli(fake.base_url,["product","view",str(ident),"--json"]).returncode)
            self.assertEqual(0,run_cli(fake.base_url,["product","edit",str(ident),"--name","renamed","--json"]).returncode)
            self.assertEqual(0,run_cli(fake.base_url,["product","delete",str(ident),"--yes","--json"]).returncode)
            missing=run_cli(fake.base_url,["product","view",str(ident),"--json"])
            self.assertEqual(1,missing.returncode)

    def test_task_state_sequence(self) -> None:
        with FakeZenTao() as fake:
            created=run_cli(fake.base_url,["task","create","--name","scenario-task","--execution","1","--json"])
            ident=json.loads(created.stdout)["id"]
            self.assertEqual(0,run_cli(fake.base_url,["task","start",str(ident),"--real-started","2026-08-25 09:00:00","--json"]).returncode)
            self.assertEqual(0,run_cli(fake.base_url,["task","finish",str(ident),"--current-consumed","1","--real-started","2026-08-25 09:00:00","--finished-date","2026-08-25 10:00:00","--json"]).returncode)
            self.assertEqual(0,run_cli(fake.base_url,["task","close",str(ident),"--json"]).returncode)
            active=run_cli(fake.base_url,["task","activate",str(ident),"--json"])
            self.assertEqual("active",json.loads(active.stdout)["status"])
            self.assertEqual(0,run_cli(fake.base_url,["task","delete",str(ident),"--yes","--json"]).returncode)


if __name__ == "__main__": unittest.main()
