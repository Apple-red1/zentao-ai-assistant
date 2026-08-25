from __future__ import annotations

import json
import unittest

from ..fake_zentao.server import FakeZenTao
from ..support import run_cli


class CliErrorSemanticsE2E(unittest.TestCase):
    def test_http_200_business_failure_is_not_success(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.view", "status_fail")
            result = run_cli(fake.base_url, ["bug", "view", "1", "--json"])
            self.assertEqual(1, result.returncode)
            self.assertEqual("", result.stdout)
            payload = json.loads(result.stderr)
            self.assertEqual("API_ERROR", payload["error"]["code"])
            self.assertEqual("fail", payload["error"]["details"]["response"]["status"])

    def test_unexpected_empty_read_response_is_not_success(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.view", "empty")
            result = run_cli(fake.base_url, ["bug", "view", "1", "--json"])
            self.assertEqual(1, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertEqual("API_ERROR", json.loads(result.stderr)["error"]["code"])

    def test_create_success_envelope_without_id_is_not_success(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.create", "success_missing_id")
            result = run_cli(fake.base_url, [
                "bug", "create", "--product", "1", "--title", "missing-id",
                "--affected-build", "trunk", "--json",
            ])
            self.assertEqual(1, result.returncode)
            self.assertEqual("", result.stdout)
            payload = json.loads(result.stderr)
            self.assertEqual("API_ERROR", payload["error"]["code"])
            self.assertEqual("id", payload["error"]["details"]["missing"])

    def test_commit_then_drop_returns_unknown_write_result_without_retry_or_follow_up(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.edit", "commit_then_drop")
            result=run_cli(fake.base_url,["bug","edit","1","--title","changed-by-cli","--json"])
            self.assertEqual(1,result.returncode,result.stderr)
            self.assertEqual("",result.stdout)
            payload=json.loads(result.stderr)
            self.assertEqual("UNKNOWN_WRITE_RESULT",payload["error"]["code"])
            self.assertEqual("changed-by-cli",fake.state.resources["bug"]["1"]["title"])
            business=[r for r in fake.state.requests if r["endpoint_id"] != "token.login"]
            self.assertEqual(["bug.edit"],[r["endpoint_id"] for r in business])

    def test_cli_get_retries_503_twice_then_returns_domain_json(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.view","503","503")
            result=run_cli(fake.base_url,["bug","view","1","--json"])
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertEqual(1,json.loads(result.stdout)["id"])
            self.assertEqual(3,len([r for r in fake.state.requests if r["endpoint_id"]=="bug.view"]))

    def test_cli_get_404_is_api_error_without_retry(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.view","404")
            result=run_cli(fake.base_url,["bug","view","1","--json"])
            self.assertEqual(1,result.returncode)
            self.assertEqual("",result.stdout)
            self.assertEqual("API_ERROR",json.loads(result.stderr)["error"]["code"])
            self.assertEqual(1,len([r for r in fake.state.requests if r["endpoint_id"]=="bug.view"]))


if __name__ == "__main__": unittest.main()
