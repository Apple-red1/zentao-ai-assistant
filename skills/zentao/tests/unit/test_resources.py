from __future__ import annotations

import unittest

from zentao_skill.internal.zentao.resources import discover_resources, display_source
from zentao_skill.services.resources.service import ResourcesService


class ResourceDiscoveryTests(unittest.TestCase):
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
