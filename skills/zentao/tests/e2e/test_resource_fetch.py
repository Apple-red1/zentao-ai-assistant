from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from ..fake_zentao.server import FakeZenTao
from ..support import TEST_HOME, run_cli


RESOURCE_ROOT = (TEST_HOME / ".zentao-ai-assistant" / "tmp" / "zentao-resources").resolve()


class ResourceFetchE2ETests(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(RESOURCE_ROOT, ignore_errors=True)

    def test_fetch_downloads_attachment_and_rich_text_resources(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources["bug"]["901"] = {
                "id": 901,
                "title": "resource bug",
                "files": {
                    "1": {"id": 1, "title": "../../错误截图.png", "url": "/assets/attachment.png?token=secret"},
                    "2": {"id": 2, "title": "same.log", "url": "/assets/one.log"},
                    "3": {"id": 3, "title": "same.log", "url": "/assets/two.log"},
                },
                "steps": """
                    <p><img src="/assets/inline.png"></p>
                    <p><a href="/assets/spec.pdf">spec</a></p>
                    <div style="background-image:url('/assets/background.webp')"></div>
                """,
            }
            fake.state.add_binary("/assets/attachment.png", b"attachment", content_type="image/png")
            fake.state.add_binary("/assets/one.log", b"one", content_type="text/plain")
            fake.state.add_binary("/assets/two.log", b"two", content_type="text/plain")
            fake.state.add_binary("/assets/inline.png", b"inline", content_type="image/png", filename="inline.png")
            fake.state.add_binary("/assets/spec.pdf", b"pdf", content_type="application/pdf", filename="spec.pdf")
            fake.state.add_binary("/assets/background.webp", b"webp", content_type="image/webp")

            result = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "901", "--json",
            ])

            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(6, len(payload["resources"]))
            self.assertEqual([], payload["partial_failures"])
            self.assertEqual("/assets/attachment.png?token=%2A%2A%2A", payload["resources"][0]["source"])
            self.assertEqual(
                ["错误截图.png", "same.log", "same-2.log", "inline.png", "spec.pdf", "background.webp"],
                [item["file_name"] for item in payload["resources"]],
            )
            for item in payload["resources"]:
                path = Path(item["local_path"])
                self.assertTrue(path.is_file(), path)
                self.assertTrue(path.is_relative_to(RESOURCE_ROOT / "bug-901"), path)
            self.assertEqual(1, len([r for r in fake.state.requests if r["endpoint_id"] == "bug.view"]))
            self.assertEqual(6, len([r for r in fake.state.requests if r["endpoint_id"] == "resource.binary"]))

    def test_fetch_keeps_successes_and_reports_partial_failures(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources["bug"]["902"] = {
                "id": 902,
                "files": [
                    {"title": "good.txt", "url": "/assets/good.txt"},
                    {"title": "missing.txt", "url": "/assets/missing.txt"},
                ],
                "steps": f'<img src="http://localhost:{fake.httpd.server_address[1]}/assets/blocked.png">',
            }
            fake.state.add_binary("/assets/good.txt", b"good", content_type="text/plain")

            result = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "902", "--json",
            ])

            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(["good.txt"], [item["file_name"] for item in payload["resources"]])
            self.assertEqual(2, len(payload["partial_failures"]))
            self.assertEqual(
                {"API_ERROR", "RESOURCE_SECURITY_ERROR"},
                {item["code"] for item in payload["partial_failures"]},
            )
            self.assertFalse(any(r.get("path") == "/assets/blocked.png" for r in fake.state.requests))

    def test_include_comments_fetches_all_comment_files_and_images_and_default_excludes_them(self) -> None:
        with FakeZenTao() as fake:
            files = []
            for index in range(5):
                file_id = 3100 + index
                content = f"attachment-{index}".encode("utf-8")
                path = f"/comment-files/{file_id}"
                fake.state.add_binary(path, content, content_type="text/plain", filename=f"attachment-{index}.txt")
                files.append({
                    "id": file_id,
                    "objectType": "comment",
                    "objectID": 1201,
                    "title": f"attachment-{index}.txt",
                    "size": len(content),
                    "url": path,
                })
            image_sources = []
            for index in range(3):
                path = f"/assets/comment-image-{index}.png"
                fake.state.add_binary(path, f"image-{index}".encode("utf-8"), content_type="image/png", filename=f"image-{index}.png")
                image_sources.append(path)
            fake.state.resources["bug"]["911"] = {
                "id": 911,
                "title": "多资源评论",
                "actions": [{
                    "id": 1201,
                    "action": "commented",
                    "objectType": "bug",
                    "objectID": 911,
                    "actor": "admin",
                    "comment": "资源评论" + "".join(f'<p><img src="{source}"></p>' for source in image_sources),
                    "files": files,
                }],
            }

            default = run_cli(fake.base_url, ["resource", "fetch", "--object-type", "bug", "--object-id", "911", "--json"])
            included = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "911", "--include-comments", "--json",
            ])

            self.assertEqual(0, default.returncode, default.stderr)
            self.assertEqual([], json.loads(default.stdout)["resources"])
            self.assertEqual(0, included.returncode, included.stderr)
            payload = json.loads(included.stdout)
            self.assertEqual([], payload["partial_failures"])
            self.assertEqual(8, len(payload["resources"]))
            self.assertTrue(all(item["origin"] == "comment" for item in payload["resources"]))
            self.assertTrue(all(item["action_id"] == 1201 for item in payload["resources"]))
            self.assertEqual(
                {f"attachment-{index}.txt" for index in range(5)} | {f"image-{index}.png" for index in range(3)},
                {item["file_name"] for item in payload["resources"]},
            )
            for item in payload["resources"]:
                self.assertEqual(Path(item["local_path"]).read_bytes(), fake.state.binary_resources[item["source"]]["content"])

    def test_fetch_rejects_http_200_html_error_and_uses_file_page_name_hints(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources["bug"]["908"] = {
                "id": 908,
                "files": [
                    {"url": "/index.php?m=file&f=read&t=png&fileID=7395"},
                    {"title": "good.txt", "url": "/assets/good-908.txt"},
                ],
            }
            fake.state.add_binary(
                "/index.php",
                b"<html><body>login redirect</body></html>",
                content_type="text/html",
            )
            fake.state.add_binary("/assets/good-908.txt", b"good", content_type="text/plain")

            result = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "908", "--json",
            ])

            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(["good.txt"], [item["file_name"] for item in payload["resources"]])
            self.assertEqual(["RESOURCE_CONTENT_INVALID"], [item["code"] for item in payload["partial_failures"]])
            self.assertNotIn("index.php", [item["file_name"] for item in payload["resources"]])
            index_requests = [
                item for item in fake.state.requests
                if item["endpoint_id"] == "resource.binary" and item["path"] == "/index.php"
            ]
            self.assertEqual(
                {"m": "file", "f": "read", "t": "png", "fileID": "7395"},
                index_requests[0]["query"],
            )

    def test_fetch_rejects_empty_and_mismatched_mime_responses(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources["bug"]["909"] = {
                "id": 909,
                "files": [
                    {"title": "empty.bin", "url": "/assets/empty.bin"},
                    {"title": "image.png", "url": "/assets/mismatch.png"},
                    {"title": "good.txt", "url": "/assets/good-909.txt"},
                ],
            }
            fake.state.add_binary("/assets/empty.bin", b"", content_type="application/octet-stream")
            fake.state.add_binary("/assets/mismatch.png", b"pdf", content_type="application/pdf")
            fake.state.add_binary("/assets/good-909.txt", b"good", content_type="text/plain")

            result = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "909", "--json",
            ])

            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(["good.txt"], [item["file_name"] for item in payload["resources"]])
            self.assertEqual(
                ["RESOURCE_CONTENT_INVALID", "RESOURCE_CONTENT_INVALID"],
                [item["code"] for item in payload["partial_failures"]],
            )

    def test_fetch_rewrites_legacy_rich_text_file_page_and_uses_query_hints(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources["bug"]["910"] = {
                "id": 910,
                "steps": '<img src="/index.php?m=file&f=read&t=png&fileID=7395">',
            }
            fake.state.add_binary("/index.php", b"png", content_type="image/png")

            result = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "910", "--json",
            ])

            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(["file-7395.png"], [item["file_name"] for item in payload["resources"]])
            self.assertEqual([], payload["partial_failures"])
            self.assertEqual(
                "/index.php?m=file&f=read&t=png&fileID=7395",
                payload["resources"][0]["source"],
            )
            index_requests = [
                item for item in fake.state.requests
                if item["endpoint_id"] == "resource.binary" and item["path"] == "/index.php"
            ]
            self.assertEqual(
                {"m": "file", "f": "download", "t": "png", "fileID": "7395"},
                index_requests[0]["query"],
            )

    def test_human_output_keeps_local_paths_and_partial_failures_visible(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources["bug"]["907"] = {
                "id": 907,
                "files": [
                    {"title": "good.txt", "url": "/assets/good-human.txt"},
                    {"title": "missing.txt", "url": "/assets/missing-human.txt"},
                ],
            }
            fake.state.add_binary("/assets/good-human.txt", b"good", content_type="text/plain")
            result = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "907",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("good.txt -> ", result.stdout)
            self.assertIn(".zentao-ai-assistant/tmp/zentao-resources/bug-907/good.txt", result.stdout)
            self.assertIn("partial_failures:", result.stdout)
            self.assertIn("API_ERROR", result.stdout)

    def test_fetch_fails_only_when_every_discovered_resource_fails(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources["bug"]["903"] = {
                "id": 903,
                "files": [{"title": "missing.txt", "url": "/assets/missing.txt"}],
            }
            result = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "903", "--json",
            ])
            self.assertEqual(1, result.returncode)
            self.assertEqual("", result.stdout)
            error = json.loads(result.stderr)["error"]
            self.assertEqual("RESOURCE_FETCH_FAILED", error["code"])
            self.assertEqual(1, len(error["details"]["partial_failures"]))

    def test_fetch_succeeds_with_empty_result_when_object_has_no_resources(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources["bug"]["904"] = {"id": 904, "title": "empty"}
            result = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "904", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual([], payload["resources"])
            self.assertEqual([], payload["partial_failures"])

    def test_fetch_accepts_same_origin_redirect_and_blocks_cross_origin_redirect(self) -> None:
        with FakeZenTao() as fake:
            port = fake.httpd.server_address[1]
            fake.state.resources["bug"]["905"] = {
                "id": 905,
                "files": [
                    {"title": "ok.bin", "url": "/assets/redirect-ok"},
                    {"title": "blocked.bin", "url": "/assets/redirect-blocked"},
                ],
            }
            fake.state.add_binary("/assets/final.bin", b"final", content_type="application/octet-stream")
            fake.state.add_redirect("/assets/redirect-ok", "/assets/final.bin")
            fake.state.add_redirect("/assets/redirect-blocked", f"http://localhost:{port}/assets/final.bin")

            result = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "905", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(["ok.bin"], [item["file_name"] for item in payload["resources"]])
            self.assertEqual(["RESOURCE_SECURITY_ERROR"], [item["code"] for item in payload["partial_failures"]])
            final_requests = [r for r in fake.state.requests if r.get("path") == "/assets/final.bin"]
            self.assertEqual(1, len(final_requests), "跨源 redirect 不得携带 Token 继续请求")

    def test_fetch_decodes_data_uri_and_never_overwrites_existing_files(self) -> None:
        with FakeZenTao() as fake:
            fake.state.resources["bug"]["906"] = {
                "id": 906,
                "steps": '<img src="data:image/png;base64,aGVsbG8=">',
            }
            first = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "906", "--json",
            ])
            second = run_cli(fake.base_url, [
                "resource", "fetch", "--object-type", "bug", "--object-id", "906", "--json",
            ])
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            first_path = Path(json.loads(first.stdout)["resources"][0]["local_path"])
            second_path = Path(json.loads(second.stdout)["resources"][0]["local_path"])
            self.assertNotEqual(first_path, second_path)
            self.assertEqual(b"hello", first_path.read_bytes())
            self.assertEqual(b"hello", second_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
