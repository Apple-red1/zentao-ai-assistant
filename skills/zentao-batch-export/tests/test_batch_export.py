from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ZENTAO_ROOT = ROOT / "skills" / "zentao"
if str(ZENTAO_ROOT) not in sys.path:
    sys.path.insert(0, str(ZENTAO_ROOT))

from tests.fake_zentao.server import FakeZenTao  # noqa: E402

SCRIPT = ROOT / "skills" / "zentao-batch-export" / "scripts" / "zentao_batch_export.py"

spec = importlib.util.spec_from_file_location("zentao_batch_export", SCRIPT)
assert spec is not None and spec.loader is not None
batch_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch_export)


def env_for(base_url: str, home: Path) -> dict[str, str]:
    env = os.environ.copy()
    config = home / ".zentao-ai-assistant" / "config.env"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        f'ZENTAO_BASE_URL="{base_url}"\n'
        'ZENTAO_ACCOUNT="admin"\n'
        'ZENTAO_PASSWORD="secret"\n',
        encoding="utf-8",
    )
    if os.name == "posix":
        config.parent.chmod(0o700)
        config.chmod(0o600)
    env.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "ZENTAO_CONFIG_FILE": str(config),
            "ZENTAO_BASE_URL": base_url,
            "ZENTAO_ACCOUNT": "admin",
            "ZENTAO_PASSWORD": "secret",
            "ZENTAO_TOKEN_CACHE_DISABLED": "1",
        }
    )
    env.pop("ZENTAO_TOKEN_CACHE_DIR", None)
    return env


def run_export(base_url: str, home: Path, *objects: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *objects, "--json"],
        cwd=ROOT,
        env=env_for(base_url, home),
        text=True,
        capture_output=True,
        timeout=40,
    )


class BatchExportUnitTests(unittest.TestCase):
    def test_parse_and_dedupe_preserve_first_seen_order(self) -> None:
        self.assertEqual(
            [("bug", 1), ("story", 2), ("product-plan", 3)],
            batch_export.normalize_object_specs(["bug:1", "story:2", "bug:1", "product-plan:3"]),
        )

    def test_invalid_type_and_id_are_rejected_before_export(self) -> None:
        with self.assertRaises(batch_export.BatchExportError) as unsupported:
            batch_export.normalize_object_specs(["project:1"])
        self.assertEqual("UNSUPPORTED_OBJECT_TYPE", unsupported.exception.code)
        with self.assertRaises(batch_export.BatchExportError) as invalid_id:
            batch_export.normalize_object_specs(["bug:0"])
        self.assertEqual("INVALID_OBJECT_ID", invalid_id.exception.code)

    def test_markdown_formats_fields_and_uses_longer_fence_for_multiline_text(self) -> None:
        content = batch_export.render_content_markdown("bug", 7, {"steps": "```nested```", "id": 7})
        self.assertIn("## steps", content)
        self.assertIn("````text", content)
        self.assertIn("```nested```", content)
        self.assertIn("## id", content)
        self.assertNotIn("```json", content)

    def test_markdown_rewrites_a_downloaded_rich_text_resource(self) -> None:
        content = batch_export.render_content_markdown(
            "bug",
            7,
            {"steps": '<p><img src="/assets/inline.png" alt="inline"></p>'},
            {"/assets/inline.png": "resources/inline.png"},
        )
        self.assertIn("![inline](<resources/inline.png>)", content)
        self.assertNotIn("/assets/inline.png", content)
        self.assertNotIn('"steps":', content)
        srcset_content = batch_export.render_content_markdown(
            "bug",
            7,
            {"steps": '<img srcset="/assets/inline.png 1x">'},
            {"/assets/inline.png": "resources/inline.png"},
        )
        self.assertIn("![inline.png](<resources/inline.png>)", srcset_content)
        unarchived_content = batch_export.render_content_markdown(
            "bug",
            7,
            {"steps": '<img src="/assets/missing.png" alt="missing">'},
        )
        self.assertIn("图片未归档", unarchived_content)
        self.assertNotIn("![missing]", unarchived_content)

    def test_copy_rejects_html_error_payload_even_if_base_result_says_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            resource_root = root / "zentao-resources"
            source_dir = resource_root / "bug-1"
            destination = root / "staging" / "resources"
            source_dir.mkdir(parents=True)
            destination.mkdir(parents=True)
            source = source_dir / "index.php"
            source.write_bytes(b"<html><body>login redirect</body></html>")

            copied, failures = batch_export._copy_resources(
                {
                    "resources": [{
                        "local_path": str(source),
                        "file_name": "index.php",
                        "content_type": "text/html",
                        "size": source.stat().st_size,
                    }],
                    "partial_failures": [],
                },
                destination,
                resource_root,
            )

            self.assertEqual(0, copied)
            self.assertEqual(["RESOURCE_CONTENT_INVALID"], [item["code"] for item in failures])
            self.assertEqual([], list(destination.iterdir()))


class BatchExportE2ETests(unittest.TestCase):
    def test_mixed_objects_export_complete_fields_resources_and_dynamic_zip(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            home = Path(td)
            fake.state.resources["bug"]["901"] = {
                "id": 901,
                "title": "资源 Bug",
                "status": "active",
                "customNested": {"items": [1, {"deep": True}]},
                "files": [{"title": "错误截图.png", "url": "/assets/attachment.png"}],
            }
            fake.state.resources["story"]["701"] = {
                "id": 701,
                "title": "混合导出需求",
                "status": "active",
                "spec": "完整需求正文",
            }
            fake.state.add_binary("/assets/attachment.png", b"attachment", content_type="image/png")

            result = run_export(fake.base_url, home, "bug:901", "story:701", "bug:901")
            self.assertEqual(0, result.returncode, result.stderr)
            output = json.loads(result.stdout)
            self.assertTrue(output["complete"])
            self.assertEqual(2, output["requested_count"])
            self.assertEqual(2, output["exported_count"])

            zip_path = Path(output["zip_path"])
            self.assertTrue(zip_path.is_file())
            self.assertRegex(zip_path.name, r"^zentao-export-\d{8}-\d{6}-[0-9a-f]{8}\.zip$")
            expected_root = home / ".zentao-ai-assistant" / "tmp" / "zentao" / "zentao-batch-export"
            self.assertTrue(zip_path.resolve().is_relative_to(expected_root.resolve()))

            with zipfile.ZipFile(zip_path) as archive:
                names = set(archive.namelist())
                self.assertIn("manifest.json", names)
                self.assertIn("objects/bug/901/content.md", names)
                self.assertIn("objects/story/701/content.md", names)
                self.assertIn("objects/bug/901/resources/错误截图.png", names)
                manifest = json.loads(archive.read("manifest.json"))
                content = archive.read("objects/bug/901/content.md").decode("utf-8")

            self.assertTrue(manifest["complete"])
            self.assertEqual(1, manifest["objects"][0]["resource_count"])
            self.assertEqual([], manifest["objects"][0]["failures"])
            self.assertIn("## customNested", content)
            self.assertIn("**deep**: `true`", content)
            self.assertIn("## files", content)
            self.assertNotIn('"customNested":', content)
            business = [request for request in fake.state.requests if request["endpoint_id"] != "token.login"]
            self.assertTrue(business)
            self.assertTrue(all(request["method"] == "GET" for request in business))

    def test_rich_text_image_reference_points_to_the_copied_zip_resource(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            home = Path(td)
            fake.state.resources["bug"]["904"] = {
                "id": 904,
                "title": "格式化详情",
                "steps": '<p>截图：</p><p><img src="/assets/inline.png" alt="inline"></p>',
            }
            fake.state.add_binary("/assets/inline.png", b"png", content_type="image/png")

            result = run_export(fake.base_url, home, "bug:904")
            self.assertEqual(0, result.returncode, result.stderr)
            output = json.loads(result.stdout)

            with zipfile.ZipFile(output["zip_path"]) as archive:
                content = archive.read("objects/bug/904/content.md").decode("utf-8")
                names = set(archive.namelist())

            self.assertIn("objects/bug/904/resources/inline.png", names)
            self.assertIn("## steps", content)
            self.assertIn("![inline](<resources/inline.png>)", content)
            self.assertNotIn("/assets/inline.png", content)
            self.assertNotIn("```json", content)
            self.assertNotIn('"steps":', content)

    def test_partial_resource_failure_keeps_zip_and_full_failure_details(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            home = Path(td)
            fake.state.resources["bug"]["902"] = {
                "id": 902,
                "title": "部分附件失败",
                "files": [
                    {"title": "good.txt", "url": "/assets/good.txt"},
                    {"title": "missing.txt", "url": "/assets/missing.txt"},
                ],
            }
            fake.state.add_binary("/assets/good.txt", b"good", content_type="text/plain")

            result = run_export(fake.base_url, home, "bug:902")
            self.assertEqual(0, result.returncode, result.stderr)
            output = json.loads(result.stdout)
            self.assertFalse(output["complete"])
            zip_path = Path(output["zip_path"])
            self.assertTrue(zip_path.is_file())

            with zipfile.ZipFile(zip_path) as archive:
                self.assertIn("objects/bug/902/resources/good.txt", archive.namelist())
                manifest = json.loads(archive.read("manifest.json"))

            item = manifest["objects"][0]
            self.assertFalse(item["complete"])
            self.assertEqual(1, item["resource_count"])
            self.assertEqual(1, len(item["failures"]))
            failure = item["failures"][0]
            self.assertEqual("resource_download", failure["stage"])
            self.assertEqual("API_ERROR", failure["code"])
            self.assertIn("details", failure)
            self.assertEqual("/assets/missing.txt", failure["details"]["source"])

    def test_html_resource_failure_keeps_zip_but_marks_object_and_package_incomplete(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            home = Path(td)
            fake.state.resources["bug"]["903"] = {
                "id": 903,
                "files": [
                    {"url": "/index.php?m=file&f=read&t=png&fileID=7395"},
                    {"title": "good.txt", "url": "/assets/good-903.txt"},
                ],
            }
            fake.state.add_binary(
                "/index.php",
                b"<html><body>login redirect</body></html>",
                content_type="text/html",
            )
            fake.state.add_binary("/assets/good-903.txt", b"good", content_type="text/plain")

            result = run_export(fake.base_url, home, "bug:903")
            self.assertEqual(0, result.returncode, result.stderr)
            output = json.loads(result.stdout)
            self.assertFalse(output["complete"])

            with zipfile.ZipFile(output["zip_path"]) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                names = set(archive.namelist())

            item = manifest["objects"][0]
            self.assertFalse(item["complete"])
            self.assertEqual(1, item["resource_count"])
            self.assertEqual(["RESOURCE_CONTENT_INVALID"], [failure["code"] for failure in item["failures"]])
            self.assertIn("objects/bug/903/resources/good.txt", names)
            self.assertNotIn("objects/bug/903/resources/index.php", names)

    def test_view_failure_does_not_block_later_object_and_failure_stub_is_packaged(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            home = Path(td)
            fake.state.resources["story"]["702"] = {"id": 702, "title": "后续对象", "status": "active"}

            result = run_export(fake.base_url, home, "bug:999999", "story:702")
            self.assertEqual(0, result.returncode, result.stderr)
            output = json.loads(result.stdout)
            self.assertFalse(output["complete"])
            self.assertEqual(2, output["requested_count"])
            self.assertEqual(1, output["exported_count"])

            with zipfile.ZipFile(output["zip_path"]) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                failed_md = archive.read("objects/bug/999999/content.md").decode("utf-8")
                success_md = archive.read("objects/story/702/content.md").decode("utf-8")

            failed = manifest["objects"][0]
            self.assertFalse(failed["complete"])
            self.assertEqual("view", failed["failures"][0]["stage"])
            self.assertTrue(failed["failures"][0]["reason"])
            self.assertIn("对象详情读取失败", failed_md)
            self.assertIn("## id\n\n`702`", success_md)

    def test_invalid_input_returns_error_without_creating_run_directory(self) -> None:
        with FakeZenTao() as fake, tempfile.TemporaryDirectory() as td:
            home = Path(td)
            result = run_export(fake.base_url, home, "project:1")
            self.assertEqual(1, result.returncode)
            self.assertEqual("", result.stdout)
            error = json.loads(result.stderr)["error"]
            self.assertEqual("UNSUPPORTED_OBJECT_TYPE", error["code"])
            export_root = home / ".zentao-ai-assistant" / "tmp" / "zentao" / "zentao-batch-export"
            self.assertFalse(export_root.exists())


if __name__ == "__main__":
    unittest.main()
