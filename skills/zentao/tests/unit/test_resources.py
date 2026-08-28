from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zentao_skill.internal.config import RuntimePaths
from zentao_skill.internal.errors import ResourceSecurityError
from zentao_skill.internal.zentao.resources import discover_resources, display_source, rewrite_legacy_file_read_url, source_file_name
from zentao_skill.services.resources.service import ResourcesService


class ResourceDiscoveryTests(unittest.TestCase):
    @staticmethod
    def _runtime_paths(base: Path) -> RuntimePaths:
        home = base / "home"
        return RuntimePaths(
            scope="user",
            config_path=home / ".zentao-ai-assistant" / "config.env",
            token_cache_root=home / ".zentao-ai-assistant" / "cache" / "auth",
            temp_root=home / ".zentao-ai-assistant" / "tmp",
        )

    def test_output_directory_uses_user_runtime_temp_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "repo"
            root.mkdir()
            runtime = self._runtime_paths(base)
            with patch("zentao_skill.services.resources.service.project_root", return_value=root, create=True), patch(
                "zentao_skill.services.resources.service.resolve_runtime_paths", return_value=runtime, create=True
            ):
                output = ResourcesService._output_directory("bug", 42)
            expected = runtime.temp_root / "zentao-resources" / "bug-42"
            self.assertEqual(expected.resolve(), output)
            self.assertTrue(output.is_dir())
            if os.name == "posix":
                self.assertEqual(0o700, output.stat().st_mode & 0o777)
            shutil.rmtree(base / "home", ignore_errors=True)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_output_directory_rejects_symlink_outside_user_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "repo"
            root.mkdir()
            runtime = self._runtime_paths(base)
            resource_root = runtime.temp_root / "zentao-resources"
            resource_root.parent.mkdir(parents=True)
            outside = base / "outside"
            outside.mkdir()
            resource_root.symlink_to(outside, target_is_directory=True)
            with patch("zentao_skill.services.resources.service.project_root", return_value=root, create=True), patch(
                "zentao_skill.services.resources.service.resolve_runtime_paths", return_value=runtime, create=True
            ):
                with self.assertRaises(ResourceSecurityError):
                    ResourcesService._output_directory("bug", 43)

    def test_discovers_attachment_and_rich_text_resources_and_deduplicates(self) -> None:
        detail = {
            "files": {
                "1": {"id": 1, "title": "截图.png", "url": "/assets/shared.png"},
                "2": {"id": 2, "title": "缺少地址.txt"},
            },
            "steps": """
                <p><img src="/assets/shared.png"></p>
                <p><a href="/assets/spec.pdf">spec</a></p>
                <div style="background-image:url('/assets/background.webp')"></div>
                <p><a href="/bug-view-2.html">普通页面链接</a></p>
            """,
        }

        candidates, failures = discover_resources(detail)
        self.assertEqual(
            ["/assets/shared.png", "/assets/spec.pdf", "/assets/background.webp"],
            [item.source for item in candidates],
        )
        self.assertEqual("attachment", candidates[0].origin)
        self.assertEqual("截图.png", candidates[0].file_name)
        self.assertEqual(1, len(failures))
        self.assertEqual("RESOURCE_URL_MISSING", failures[0]["code"])

    def test_discovers_srcset_poster_and_style_block_resources(self) -> None:
        detail = {
            "desc": """
                <picture><source srcset="/assets/one.webp 1x, /assets/two.webp 2x"></picture>
                <video poster="/assets/poster.jpg"></video>
                <style>.hero { background:url('/assets/style.png') }</style>
            """,
        }
        candidates, failures = discover_resources(detail)
        self.assertEqual([], failures)
        self.assertEqual(
            ["/assets/one.webp", "/assets/two.webp", "/assets/poster.jpg", "/assets/style.png"],
            [item.source for item in candidates],
        )

    def test_does_not_scan_audit_history_or_diff_as_current_resources(self) -> None:
        detail = {
            "desc": '<p><img src="/assets/current.png"></p>',
            "actions": [{"history": [{"diff": '<img src="/assets/old.png">'}]}],
        }
        candidates, failures = discover_resources(detail)
        self.assertEqual([], failures)
        self.assertEqual(["/assets/current.png"], [item.source for item in candidates])

    def test_source_file_name_uses_file_page_query_hints(self) -> None:
        source = "/index.php?m=file&f=read&t=png&fileID=7395"
        self.assertEqual("file-7395.png", source_file_name(source))
        self.assertIsNone(source_file_name("/index.php?m=file&f=read"))

    def test_rewrites_legacy_image_read_url_to_download_and_preserves_source_shape(self) -> None:
        source = "http://localhost/index.php?m=file&f=read&t=png&fileID=7395&foo=bar"
        self.assertEqual(
            "http://localhost/index.php?m=file&f=download&t=png&fileID=7395&foo=bar",
            rewrite_legacy_file_read_url(source),
        )

    def test_does_not_rewrite_non_legacy_or_non_image_urls(self) -> None:
        sources = (
            "/assets/image.png",
            "/index.php?m=file&f=download&t=png&fileID=7395",
            "/index.php?m=file&f=read&t=txt&fileID=7395",
            "/index.php?m=file&f=read&t=png",
            "/index.php?m=file&f=read&t=png&fileID=0",
            "/index.php?m=file&f=read&t=png&fileID=7395&fileID=7396",
            "data:image/png;base64,aGVsbG8=",
        )
        for source in sources:
            with self.subTest(source=source):
                self.assertEqual(source, rewrite_legacy_file_read_url(source))

    def test_output_source_redacts_embedded_data_and_sensitive_query_values(self) -> None:
        self.assertEqual("data:image/png;base64,...", display_source("data:image/png;base64,aGVsbG8="))
        self.assertEqual(
            "/assets/file.png?token=%2A%2A%2A&name=ok",
            display_source("/assets/file.png?token=secret&name=ok"),
        )
        self.assertEqual(
            "https://***@localhost:8080/file.png?token=%2A%2A%2A",
            display_source("https://user:secret@localhost:8080/file.png?token=secret"),
        )
        self.assertEqual("[invalid resource URL]", display_source("http" + "://[invalid"))

    def test_file_names_cannot_escape_tmp_and_are_cross_platform_safe(self) -> None:
        self.assertEqual("evil.txt", ResourcesService._safe_filename("../../evil.txt"))
        self.assertEqual("bad_name_.txt", ResourcesService._safe_filename('bad:name?.txt'))
        self.assertEqual("_CON.txt", ResourcesService._safe_filename("CON.txt"))

    def test_discovers_data_uri_as_rich_text_resource(self) -> None:
        candidates, failures = discover_resources({"steps": '<img src="data:image/png;base64,aGVsbG8=">'})
        self.assertEqual([], failures)
        self.assertEqual(1, len(candidates))
        self.assertTrue(candidates[0].source.startswith("data:image/png;base64,"))
        self.assertEqual("rich_text", candidates[0].origin)


if __name__ == "__main__":
    unittest.main()
