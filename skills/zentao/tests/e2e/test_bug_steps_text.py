from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ..fake_zentao.server import FakeZenTao
from ..support import run_cli


class BugStepsTextE2E(unittest.TestCase):
    def test_json_text_decodes_one_serialization_boundary(self) -> None:
        expected = "1. 打开页面\n2. 输入 URL=http://localhost:8080?a=1&b=2\n\n实际结果：\n出现错误"
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "bug", "create", "--product", "1", "--title", "多行步骤",
                "--affected-build", "trunk", "--steps-json", json.dumps(expected), "--json",
            ])

            self.assertEqual(0, result.returncode, result.stderr)
            request = next(item for item in fake.state.requests if item["endpoint_id"] == "bug.create")
            self.assertEqual(expected, request["body"]["steps"])
            self.assertEqual(expected, json.loads(result.stdout)["steps"])

    def test_json_text_preserves_explicit_literal_backslash_n(self) -> None:
        expected = r"用户明确输入字面量 \n，不应被改写"
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "bug", "create", "--product", "1", "--title", "字面量",
                "--affected-build", "trunk", "--steps-json", json.dumps(expected), "--json",
            ])

            self.assertEqual(0, result.returncode, result.stderr)
            request = next(item for item in fake.state.requests if item["endpoint_id"] == "bug.create")
            self.assertEqual(expected, request["body"]["steps"])
            self.assertNotIn("\n", request["body"]["steps"])

    def test_json_text_is_used_for_edit(self) -> None:
        expected = "编辑后的第一行\n编辑后的第二行"
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "bug", "edit", "1", "--steps-json", json.dumps(expected), "--json",
            ])

            self.assertEqual(0, result.returncode, result.stderr)
            request = next(item for item in fake.state.requests if item["endpoint_id"] == "bug.edit")
            self.assertEqual(expected, request["body"]["steps"])

    def test_direct_and_file_steps_normalize_actual_crlf_without_decoding_literal(self) -> None:
        expected = "第一行\n第二行\n第三行\\n仍是字面量"
        with tempfile.TemporaryDirectory() as td, FakeZenTao() as fake:
            path = Path(td) / "steps.txt"
            path.write_bytes("第一行\r\n第二行\r第三行\\n仍是字面量".encode("utf-8"))
            file_result = run_cli(fake.base_url, [
                "bug", "create", "--product", "1", "--title", "文件步骤",
                "--affected-build", "trunk", "--steps-file", str(path), "--json",
            ])
            direct_result = run_cli(fake.base_url, [
                "bug", "edit", "1", "--steps", "第一行\r\n第二行\r第三行\\n仍是字面量", "--json",
            ])

            self.assertEqual(0, file_result.returncode, file_result.stderr)
            self.assertEqual(0, direct_result.returncode, direct_result.stderr)
            requests = [
                item for item in fake.state.requests
                if item["endpoint_id"] in {"bug.create", "bug.edit"}
            ]
            self.assertEqual([expected, expected], [item["body"]["steps"] for item in requests])

    def test_invalid_json_steps_fails_before_any_business_request(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "bug", "create", "--product", "1", "--title", "错误输入",
                "--affected-build", "trunk", "--steps-json", "not-json", "--json",
            ])

            self.assertEqual(2, result.returncode)
            self.assertEqual("USAGE_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], [item for item in fake.state.requests if item["endpoint_id"] != "token.login"])


if __name__ == "__main__":
    unittest.main()
