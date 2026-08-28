from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ..fake_zentao.server import FakeZenTao
from ..support import run_cli
from zentao_skill.comment_contract import web_object_type
from zentao_skill.cli.main import CLI_ENDPOINT_IDS


COMMENT_RESOURCES = (
    "bug",
    "story",
    "product",
    "task",
    "execution",
    "project",
    "test-task",
    "product-plan",
    "release",
    "build",
)


class CommentCliTests(unittest.TestCase):
    def test_all_verified_resources_expose_comment_help(self) -> None:
        with FakeZenTao() as fake:
            for resource in COMMENT_RESOURCES:
                with self.subTest(resource=resource):
                    result = run_cli(fake.base_url, [resource, "comment", "--help"])
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertIn("comment", result.stdout)
            self.assertEqual([], fake.state.requests)

    def test_unsupported_file_and_inline_combinations_fail_before_web_request(self) -> None:
        with FakeZenTao() as fake:
            cases = (
                ["product", "comment", "1", "--comment", "hello", "--file", "${FIXTURE_FILE}", "--json"],
                ["story", "comment", "1", "--comment", "hello", "--inline-image", "${FIXTURE_FILE}", "--json"],
            )
            for argv in cases:
                result = run_cli(fake.base_url, argv)
                self.assertNotEqual(0, result.returncode, result.stdout)
                self.assertEqual("", result.stdout)
            self.assertEqual([], fake.state.requests)

    def test_comment_body_is_required_and_comment_sources_are_mutually_exclusive(self) -> None:
        with FakeZenTao() as fake:
            cases = (
                ["bug", "comment", "1", "--json"],
                ["bug", "comment", "1", "--comment", "", "--json"],
                ["bug", "comment", "1", "--comment", "one", "--comment-file", "missing.txt", "--json"],
            )
            for argv in cases:
                with self.subTest(argv=argv):
                    result = run_cli(fake.base_url, argv)
                    self.assertNotEqual(0, result.returncode)
                    self.assertEqual("", result.stdout)
                    self.assertEqual("USAGE_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], fake.state.requests)

    def test_comment_is_not_an_official_api_endpoint(self) -> None:
        self.assertFalse(any(item.endswith(".comment") for item in CLI_ENDPOINT_IDS))

    def test_all_ten_supported_objects_round_trip_through_fixed_web_comment(self) -> None:
        with FakeZenTao() as fake:
            for resource in COMMENT_RESOURCES:
                with self.subTest(resource=resource):
                    result = run_cli(fake.base_url, [resource, "comment", "1", "--comment", f"评论-{resource}", "--json"])
                    self.assertEqual(0, result.returncode, result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual("success", payload["status"])
                    self.assertEqual(resource, payload["object_type"])
                    self.assertEqual("commented", payload["action"])
            writes = [item for item in fake.state.requests if item["endpoint_id"] == "web.comment"]
            self.assertEqual(10, len(writes))
            self.assertEqual(
                {web_object_type(resource) for resource in COMMENT_RESOURCES},
                {item["query"]["objectType"] for item in writes},
            )

    def test_bug_and_story_accept_repeatable_unicode_files_with_same_names(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first_dir = root / "one"
            second_dir = root / "two"
            first_dir.mkdir()
            second_dir.mkdir()
            first = first_dir / "同名.txt"
            second = second_dir / "同名.txt"
            first.write_bytes("第一份".encode("utf-8"))
            second.write_bytes("第二份内容".encode("utf-8"))

            for resource in ("bug", "story"):
                result = run_cli(
                    fake.base_url,
                    [resource, "comment", "1", "--comment", "附件评论", "--file", str(first), "--file", str(second), "--json"],
                )
                self.assertEqual(0, result.returncode, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(2, len(payload["file_ids"]))

            writes = [item for item in fake.state.requests if item["endpoint_id"] == "web.comment"]
            self.assertEqual(2, len(writes))
            self.assertEqual([["同名.txt", "同名.txt"], ["同名.txt", "同名.txt"]], [
                [file["name"] for file in write["body"]["files[]"]] for write in writes
            ])

    def test_bug_inline_image_is_uploaded_once_and_is_downloadable_as_comment_resource(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            image = Path(td) / "截图.png"
            image.write_bytes(b"PNG-DATA")
            result = run_cli(
                fake.base_url,
                ["bug", "comment", "1", "--comment", "图片评论", "--inline-image", str(image), "--json"],
            )
            self.assertEqual(0, result.returncode, result.stderr)
            comment = json.loads(result.stdout)
            self.assertEqual("success", comment["status"])
            self.assertEqual(1, len([item for item in fake.state.requests if item["endpoint_id"] == "web.inline_upload"]))
            self.assertEqual(1, len([item for item in fake.state.requests if item["endpoint_id"] == "web.comment"]))

            resource_result = run_cli(
                fake.base_url,
                ["resource", "fetch", "--object-type", "bug", "--object-id", "1", "--include-comments", "--json"],
            )
            self.assertEqual(0, resource_result.returncode, resource_result.stderr)
            resources = json.loads(resource_result.stdout)["resources"]
            self.assertEqual(1, len(resources))
            self.assertEqual("comment", resources[0]["origin"])
            self.assertEqual("actions.comment", resources[0]["field"])
            self.assertEqual(b"PNG-DATA", Path(resources[0]["local_path"]).read_bytes())
            downloads = [item for item in fake.state.requests if item["endpoint_id"] == "resource.binary"]
            self.assertEqual({"m": "file", "f": "download", "t": "png", "fileID": str(comment["inline_file_id"])}, downloads[0]["query"])

    def test_unknown_comment_write_is_read_back_once_without_repost(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_web_faults("comment", "200_no_persist")
            result = run_cli(fake.base_url, ["bug", "comment", "1", "--comment", "not persisted", "--json"])
            self.assertEqual(1, result.returncode)
            error = json.loads(result.stderr)["error"]
            self.assertEqual("UNKNOWN_WRITE_RESULT", error["code"])
            self.assertEqual(1, len([item for item in fake.state.requests if item["endpoint_id"] == "web.comment"]))
            self.assertEqual([], fake.state.resources["bug"]["1"].get("actions", []))

    def test_unknown_inline_upload_stops_before_comment_and_definite_failure_does_too(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            image = Path(td) / "image.png"
            image.write_bytes(b"PNG")
            fake.state.plan_web_faults("inline_upload", "malformed")
            result = run_cli(fake.base_url, ["bug", "comment", "1", "--comment", "image", "--inline-image", str(image), "--json"])
            self.assertEqual(1, result.returncode)
            error = json.loads(result.stderr)["error"]
            self.assertEqual("UNKNOWN_WRITE_RESULT", error["code"])
            self.assertTrue(error["details"]["possible_orphan"])
            self.assertFalse(any(item["endpoint_id"] == "web.comment" for item in fake.state.requests))

            fake.state.plan_web_faults("inline_upload", "500")
            result = run_cli(fake.base_url, ["bug", "comment", "1", "--comment", "image", "--inline-image", str(image), "--json"])
            self.assertEqual(1, result.returncode)
            self.assertEqual("API_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertFalse(any(item["endpoint_id"] == "web.comment" for item in fake.state.requests))


if __name__ == "__main__":
    unittest.main()
