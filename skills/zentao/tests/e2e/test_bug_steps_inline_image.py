from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ..fake_zentao.server import FakeZenTao
from ..support import run_cli


class BugStepsInlineImageE2E(unittest.TestCase):
    def test_create_embeds_image_in_steps_without_comment_fallback(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            image = Path(td) / "页面截图.png"
            image.write_bytes(b"PNG-DATA")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "步骤图片",
                    "--affected-build", "trunk", "--steps", "复现步骤",
                    "--steps-inline-image", str(image), "--json",
                ],
            )

            self.assertEqual(0, result.returncode, result.stderr)
            created = json.loads(result.stdout)
            self.assertEqual(100, created["id"])
            self.assertIn("<img", created["steps"])
            self.assertNotIn("web.comment", [item["endpoint_id"] for item in fake.state.requests])
            self.assertEqual(1, len([item for item in fake.state.requests if item["endpoint_id"] == "web.inline_upload"]))
            self.assertEqual(1, len([item for item in fake.state.requests if item["endpoint_id"] == "web.bug.create"]))
            self.assertEqual([], fake.state.resources["bug"]["100"].get("actions", []))

    def test_edit_embeds_image_in_steps_without_comment_fallback(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            image = Path(td) / "编辑截图.png"
            image.write_bytes(b"EDIT-PNG")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "edit", "1", "--steps", "更新后的步骤",
                    "--steps-inline-image", str(image), "--json",
                ],
            )

            self.assertEqual(0, result.returncode, result.stderr)
            edited = json.loads(result.stdout)
            self.assertEqual(1, edited["id"])
            self.assertIn("<img", edited["steps"])
            self.assertNotIn("web.comment", [item["endpoint_id"] for item in fake.state.requests])
            self.assertEqual(1, len([item for item in fake.state.requests if item["endpoint_id"] == "web.inline_upload"]))
            self.assertEqual(1, len([item for item in fake.state.requests if item["endpoint_id"] == "web.bug.edit"]))
            self.assertEqual([], fake.state.resources["bug"]["1"].get("actions", []))

    def test_hidden_uid_form_remains_compatible(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            fake.state.bug_form_uid_fields = [("hidden", "legacy-hidden-uid")]
            image = Path(td) / "legacy.png"
            image.write_bytes(b"LEGACY-PNG")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "隐藏 uid 兼容",
                    "--affected-build", "trunk", "--steps", "步骤",
                    "--steps-inline-image", str(image), "--json",
                ],
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("<img", json.loads(result.stdout)["steps"])
            self.assertEqual(1, len([item for item in fake.state.requests if item["endpoint_id"] == "web.bug.create"]))

    def test_missing_uid_stops_before_upload_or_bug_write(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            fake.state.bug_form_uid_fields = []
            image = Path(td) / "missing-uid.png"
            image.write_bytes(b"MISSING-UID")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "缺少 uid",
                    "--affected-build", "trunk", "--steps-inline-image", str(image), "--json",
                ],
            )

            self.assertEqual(1, result.returncode)
            self.assertEqual("API_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], [item for item in fake.state.requests if item["endpoint_id"] in {"web.inline_upload", "web.bug.create"}])
            self.assertNotIn("100", fake.state.resources["bug"])

    def test_empty_uid_stops_before_upload_or_bug_write(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            fake.state.bug_form_uid_fields = [("text", "   ")]
            image = Path(td) / "empty-uid.png"
            image.write_bytes(b"EMPTY-UID")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "空 uid",
                    "--affected-build", "trunk", "--steps-inline-image", str(image), "--json",
                ],
            )

            self.assertEqual(1, result.returncode)
            self.assertEqual("API_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], [item for item in fake.state.requests if item["endpoint_id"] in {"web.inline_upload", "web.bug.create"}])
            self.assertNotIn("100", fake.state.resources["bug"])

    def test_conflicting_uid_controls_stop_before_upload_or_bug_write(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            fake.state.bug_form_uid_fields = [("hidden", "one"), ("text", "two")]
            image = Path(td) / "conflicting-uid.png"
            image.write_bytes(b"CONFLICTING-UID")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "冲突 uid",
                    "--affected-build", "trunk", "--steps-inline-image", str(image), "--json",
                ],
            )

            self.assertEqual(1, result.returncode)
            self.assertEqual("API_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], [item for item in fake.state.requests if item["endpoint_id"] in {"web.inline_upload", "web.bug.create"}])
            self.assertNotIn("100", fake.state.resources["bug"])

    def test_steps_text_is_escaped_and_image_order_and_duplicates_are_preserved(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = root / "一.png"
            second = root / "二.png"
            first.write_bytes(b"ONE")
            second.write_bytes(b"TWO")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "步骤安全",
                    "--affected-build", "trunk", "--steps", '<script>alert("x")</script> &',
                    "--steps-inline-image", str(first), "--steps-inline-image", str(second),
                    "--steps-inline-image", str(first), "--json",
                ],
            )

            self.assertEqual(0, result.returncode, result.stderr)
            steps = json.loads(result.stdout)["steps"]
            self.assertIn("&lt;script&gt;alert(\"x\")&lt;/script&gt; &amp;", steps)
            self.assertNotIn("<script", steps)
            self.assertEqual(2, steps.count("fileID=5000"))
            self.assertEqual(1, steps.count("fileID=5001"))
            self.assertLess(steps.index("fileID=5000"), steps.index("fileID=5001"))
            self.assertEqual(2, len([item for item in fake.state.requests if item["endpoint_id"] == "web.inline_upload"]))

    def test_invalid_local_step_image_fails_before_any_request(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "无效图片",
                    "--affected-build", "trunk", "--steps-inline-image", "missing.png", "--json",
                ],
            )

            self.assertEqual(2, result.returncode)
            self.assertEqual("USAGE_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], fake.state.requests)

    def test_unknown_step_image_upload_stops_without_bug_write_or_retry(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            image = Path(td) / "unknown.png"
            image.write_bytes(b"UNKNOWN")
            fake.state.plan_web_faults("inline_upload", "commit_then_drop")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "上传未知",
                    "--affected-build", "trunk", "--steps-inline-image", str(image), "--json",
                ],
            )

            self.assertEqual(1, result.returncode)
            error = json.loads(result.stderr)["error"]
            self.assertEqual("UNKNOWN_WRITE_RESULT", error["code"])
            self.assertTrue(error["details"]["possible_orphan"])
            self.assertEqual([], [item for item in fake.state.requests if item["endpoint_id"] == "web.bug.create"])
            self.assertNotIn("100", fake.state.resources["bug"])

    def test_unknown_create_write_is_not_retried(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            image = Path(td) / "created.png"
            image.write_bytes(b"CREATED")
            fake.state.plan_web_faults("bug_create", "commit_then_drop")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "提交未知",
                    "--affected-build", "trunk", "--steps-inline-image", str(image), "--json",
                ],
            )

            self.assertEqual(1, result.returncode)
            self.assertEqual("UNKNOWN_WRITE_RESULT", json.loads(result.stderr)["error"]["code"])
            self.assertEqual(1, len([item for item in fake.state.requests if item["endpoint_id"] == "web.bug.create"]))
            self.assertIn("100", fake.state.resources["bug"])

    def test_resource_fetch_discovers_created_steps_image(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            image = Path(td) / "可下载.png"
            image.write_bytes(b"DOWNLOAD-ME")
            create = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "可下载",
                    "--affected-build", "trunk", "--steps", "步骤",
                    "--steps-inline-image", str(image), "--json",
                ],
            )
            self.assertEqual(0, create.returncode, create.stderr)
            fetched = run_cli(fake.base_url, ["resource", "fetch", "--object-type", "bug", "--object-id", "100", "--json"])
            self.assertEqual(0, fetched.returncode, fetched.stderr)
            resources = json.loads(fetched.stdout)["resources"]
            self.assertEqual(1, len(resources))
            self.assertIn("fileID=5000", resources[0]["source"])
            self.assertEqual(b"DOWNLOAD-ME", Path(resources[0]["local_path"]).read_bytes())

    def test_image_upload_for_create_is_fail_closed_before_business_write(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            image = Path(td) / "forbidden.png"
            image.write_bytes(b"FORBIDDEN")
            fake.state.plan_web_faults("inline_upload", "403")
            result = run_cli(
                fake.base_url,
                [
                    "bug", "create", "--product", "1", "--title", "不应创建",
                    "--affected-build", "trunk", "--steps", "步骤",
                    "--steps-inline-image", str(image), "--json",
                ],
            )

            self.assertEqual(1, result.returncode)
            self.assertEqual("API_ERROR", json.loads(result.stderr)["error"]["code"])
            business_writes = {
                item["endpoint_id"]
                for item in fake.state.requests
                if item["endpoint_id"] in {"bug.create", "web.bug.create", "web.comment"}
            }
            self.assertEqual(set(), business_writes)
            self.assertNotIn("100", fake.state.resources["bug"])


if __name__ == "__main__":
    unittest.main()
