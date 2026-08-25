
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
            items_by_id = {item["endpoint_id"]: item for item in CATALOG}
            for outcome in outcomes:
                endpoint_id=outcome["endpoint_id"]
                with self.subTest(endpoint=endpoint_id):
                    self.assertEqual(0,outcome["returncode"],msg=f"{endpoint_id}\nstdout={outcome['stdout']}\nstderr={outcome['stderr']}")
                    self.assertTrue(outcome["stdout"].strip())
                    payload = json.loads(outcome["stdout"])
                    self._assert_business_success(items_by_id[endpoint_id], payload)
            business_counts=Counter(r["endpoint_id"] for r in fake.state.requests if r["endpoint_id"] != "token.login")
            for item in CATALOG:
                if item["endpoint_id"] != "token.login":
                    self.assertEqual(1,business_counts[item["endpoint_id"]],item["endpoint_id"])
            self.assertGreaterEqual(sum(1 for r in fake.state.requests if r["endpoint_id"]=="token.login"),1)

    def _assert_business_success(self, item: dict[str, object], payload: object) -> None:
        """Check the minimum semantic response contract, not just JSON syntax."""
        endpoint_id = str(item["endpoint_id"])
        operation = str(item["operation"])
        resource = str(item["resource"])
        self.assertIsInstance(payload, (dict, str), endpoint_id)
        if endpoint_id == "token.login":
            self.assertIsInstance(payload, dict)
            self.assertEqual("ok", payload.get("status"))
            self.assertTrue(payload.get("base_url"))
            self.assertTrue(payload.get("account"))
            return
        if operation == "delete":
            self.assertIsInstance(payload, dict)
            self.assertEqual("success", payload.get("status"), endpoint_id)
            self.assertIn("id", payload, endpoint_id)
            return
        self.assertNotEqual("fail", payload.get("status") if isinstance(payload, dict) else None, endpoint_id)
        if operation == "create" or operation == "upload":
            self.assertIsInstance(payload, dict)
            self.assertIn("id", payload, endpoint_id)
        elif operation.startswith("list"):
            self.assertIsInstance(payload, dict)
            collection = resource.replace("-", "") + "s"
            self.assertIn(collection, payload, endpoint_id)
            self.assertIsInstance(payload[collection], list, endpoint_id)
        elif operation == "view":
            self.assertIsInstance(payload, dict)
            self.assertIn("id", payload, endpoint_id)
        else:
            self.assertIsInstance(payload, dict)
            self.assertIn("id", payload, endpoint_id)

    def test_business_failure_and_shape_matrix_is_not_a_success(self) -> None:
        cases = (
            ("bug.view", ["bug", "view", "1", "--json"], "status_fail"),
            ("bug.view", ["bug", "view", "1", "--json"], "empty"),
            ("bug.create", ["bug", "create", "--product", "1", "--title", "missing-id", "--affected-build", "trunk", "--json"], "success_missing_id"),
            ("bug.list_product", ["bug", "list", "--product", "1", "--json"], "success_missing_collection"),
            ("bug.view", ["bug", "view", "1", "--json"], "malformed_json"),
        )
        for endpoint_id, argv, fault in cases:
            with self.subTest(endpoint=endpoint_id, fault=fault), FakeZenTao() as fake:
                fake.state.plan_faults(endpoint_id, fault)
                result = run_cli(fake.base_url, argv)
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertEqual("", result.stdout)
                self.assertEqual("API_ERROR" if fault != "malformed_json" else "MALFORMED_RESPONSE", json.loads(result.stderr)["error"]["code"])

        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, ["bug", "delete", "1", "--yes", "--json"])
            self.assertEqual(0, result.returncode, result.stderr)
            self._assert_business_success(next(item for item in CATALOG if item["endpoint_id"] == "bug.delete"), json.loads(result.stdout))

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
