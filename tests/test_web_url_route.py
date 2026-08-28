from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "zentao" / "scripts"))

from zentao_skill.internal.web_urls import render_bug_web_urls  # noqa: E402
from zentao_skill.cli.main import main as cli_main  # noqa: E402


class WebUrlRouteTests(unittest.TestCase):
    def run_cli(self, *ids: str, base_url: str = "https://localhost/zentao/") -> tuple[int, str, str]:
        """Exercise the public CLI with isolated config and all network forbidden."""
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "fixture.env"
            config.write_text(
                f"ZENTAO_BASE_URL={base_url}\n"
                "ZENTAO_ACCOUNT=fixture\nZENTAO_PASSWORD=fixture-only\n",
                encoding="utf-8",
            )
            stdout, stderr = io.StringIO(), io.StringIO()
            with (
                patch.dict(os.environ, {"ZENTAO_CONFIG_FILE": str(config), "ZENTAO_TOKEN_CACHE_DISABLED": "1"}, clear=True),
                patch("pathlib.Path.home", return_value=Path(td)),
                patch("socket.socket.connect", side_effect=AssertionError("Network is forbidden")),
                patch("webbrowser.open", side_effect=AssertionError("Browser is forbidden")),
                patch("zentao_skill.internal.zentao.session.ZentaoSession.ensure_login", side_effect=AssertionError("Login is forbidden")),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = cli_main(["bug", "web-url", *ids, "--json"])
            return code, stdout.getvalue(), stderr.getvalue()

    def test_fixed_route_supports_single_and_batch_ids_without_network(self) -> None:
        one = render_bug_web_urls("http://localhost", [3641])
        many = render_bug_web_urls("http://localhost", [1, 2, 3, 4, 5])
        self.assertEqual("http://localhost/index.php?m=bug&f=view&bugID=3641", one[0]["url"])
        self.assertEqual(5, len(many))
        self.assertTrue(all(item["source"] == "zentao_standard_route" for item in many))

    def test_cli_single_and_batch_keep_raw_id_and_response_shape(self) -> None:
        for ids in (("123",), ("124", "123", "124")):
            with self.subTest(ids=ids):
                code, stdout, stderr = self.run_cli(*ids)
                self.assertEqual((0, ""), (code, stderr))
                payload = json.loads(stdout)
                self.assertIsInstance(payload, dict if len(ids) == 1 else list)
                rows = [payload] if isinstance(payload, dict) else payload
                self.assertEqual([int(value) for value in ids], [row["id"] for row in rows])
                for row in rows:
                    self.assertEqual({"resource", "id", "url", "source", "verified"}, set(row))
                    self.assertIs(type(row["id"]), int)
                    self.assertEqual("bug", row["resource"])
                    self.assertEqual("zentao_standard_route", row["source"])
                    self.assertIs(row["verified"], True)
                    self.assertEqual(
                        f"https://localhost/zentao/index.php?m=bug&f=view&bugID={row['id']}",
                        row["url"],
                    )

    def test_cli_id_mapping_is_independent_of_batch_order_and_instance(self) -> None:
        for base in ("https://localhost/", "http://localhost:8123/team/"):
            with self.subTest(base=base):
                code, stdout, stderr = self.run_cli("124", "123", base_url=base)
                self.assertEqual((0, ""), (code, stderr))
                by_id = {row["id"]: row["url"] for row in json.loads(stdout)}
                for item_id in (123, 124):
                    code, single, stderr = self.run_cli(str(item_id), base_url=base)
                    self.assertEqual((0, ""), (code, stderr))
                    self.assertEqual(json.loads(single)["url"], by_id[item_id])
                    self.assertEqual(f"{base.rstrip('/')}/index.php?m=bug&f=view&bugID={item_id}", by_id[item_id])

    def test_cli_invalid_id_keeps_error_contract_without_network(self) -> None:
        for item_id in ("0", "-1", "not-an-id"):
            with self.subTest(item_id=item_id):
                code, stdout, stderr = self.run_cli(item_id)
                self.assertEqual((2, ""), (code, stdout))
                self.assertEqual("USAGE_ERROR", json.loads(stderr)["error"]["code"])


if __name__ == "__main__":
    unittest.main()
