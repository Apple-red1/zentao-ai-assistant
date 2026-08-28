from __future__ import annotations

import json
import tempfile
import unittest
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from zentao_skill.internal.config import Config
from zentao_skill.internal.errors import ApiError, UnknownWriteResult
from zentao_skill.internal.http.legacy import LegacyPageFailure, LegacyWebClient
from zentao_skill.internal.zentao.files import FilesAPI


class LegacyUploadPageTests(unittest.TestCase):
    def test_page_client_logs_in_and_submits_files_array_to_bug_edit_form(self) -> None:
        state: dict[str, object] = {"login_fields": {}, "upload_fields": {}, "file_name": None, "file_bytes": b""}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                split = urlsplit(self.path)
                if split.path != "/index.php":
                    self._send(404, "not found")
                    return
                query = parse_qs(split.query)
                if query.get("m") == ["user"] and query.get("f") == ["login"]:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Set-Cookie", "sid=login; Path=/")
                    self.end_headers()
                    self.wfile.write(b'<form><input name="account"><input name="password"></form>')
                    return
                if query.get("m") == ["bug"] and query.get("f") == ["edit"]:
                    if "auth=ok" not in self.headers.get("Cookie", ""):
                        self._send(403, "not authenticated")
                        return
                    self._send(
                        200,
                        '<form action="/index.php?m=bug&amp;f=edit&amp;bugID=7" method="post">'
                        '<input type="hidden" name="csrf" value="csrf-value">'
                        '<input type="hidden" name="id" value="7">'
                        '<input name="title" value="old title"></form>',
                    )
                    return
                self._send(404, "not found")

            def do_POST(self) -> None:
                split = urlsplit(self.path)
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length)
                query = parse_qs(split.query)
                if query.get("m") == ["user"] and query.get("f") == ["login"]:
                    fields = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
                    state["login_fields"] = {key: values[-1] for key, values in fields.items()}
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Set-Cookie", "auth=ok; Path=/")
                    self.end_headers()
                    self.wfile.write(b"<html>home</html>")
                    return
                if query.get("m") == ["bug"] and query.get("f") == ["edit"]:
                    if "auth=ok" not in self.headers.get("Cookie", ""):
                        self._send(403, "not authenticated")
                        return
                    content_type = self.headers.get("Content-Type", "")
                    message = BytesParser(policy=default).parsebytes(
                        ("Content-Type: " + content_type + "\r\nMIME-Version: 1.0\r\n\r\n").encode() + raw
                    )
                    fields: dict[str, str] = {}
                    for part in message.iter_parts():
                        name = part.get_param("name", header="content-disposition")
                        if not name:
                            continue
                        filename = part.get_filename()
                        if filename:
                            state["file_name"] = filename
                            state["file_bytes"] = part.get_payload(decode=True) or b""
                        else:
                            fields[name] = part.get_content()
                    state["upload_fields"] = fields
                    self._send(200, "<html>saved</html>")
                    return
                self._send(404, "not found")

            def _send(self, status: int, body: str) -> None:
                raw = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                file_path = Path(td) / "fixture.txt"
                file_path.write_bytes(b"legacy-page-payload")
                client = LegacyWebClient(
                    base_url=f"http://127.0.0.1:{server.server_address[1]}",
                    account="admin",
                    password="secret",
                )
                response = client.upload_bug_attachment(
                    bug_id=7,
                    fields=[("id", 7), ("title", "Bug title"), ("openedBuild[]", "trunk")],
                    file=file_path,
                )
            self.assertEqual(200, response.status)
            self.assertEqual("3", state["login_fields"]["passwordStrength"])
            self.assertEqual("csrf-value", state["upload_fields"]["csrf"])
            self.assertEqual("Bug title", state["upload_fields"]["title"])
            self.assertEqual("trunk", state["upload_fields"]["openedBuild[]"])
            self.assertEqual("fixture.txt", state["file_name"])
            self.assertEqual(b"legacy-page-payload", state["file_bytes"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class FileUploadFallbackTests(unittest.TestCase):
    @staticmethod
    def _empty_v2_error() -> ApiError:
        return ApiError(
            "ZenTao API 返回空响应",
            {"method": "POST", "path": "/files", "response": None},
        )

    @staticmethod
    def _detail(files: object) -> dict[str, object]:
        return {
            "bug": {
                "id": 7,
                "title": "Bug title",
                "openedBuild": "trunk",
                "product": 2,
                "branch": 0,
                "module": 0,
                "project": 0,
                "execution": 0,
                "plan": 0,
                "story": 0,
                "task": 0,
                "case": 0,
                "testtask": 0,
                "severity": 1,
                "pri": 1,
                "type": "codeerror",
                "steps": "<p>steps</p>",
                "status": "active",
                "files": files,
            }
        }

    def test_empty_v2_response_falls_back_once_and_returns_readback_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / "proof.txt"
            file_path.write_bytes(b"proof")
            session = Mock()
            session.config = Config("http://127.0.0.1:1", "admin", "secret")
            session.post.side_effect = self._empty_v2_error()
            api = FilesAPI(session)
            api._bugs.view = Mock(side_effect=[self._detail({}), self._detail({"8": {
                "id": 8,
                "title": "proof.txt",
                "name": "proof.txt",
                "size": 5,
                "url": "/index.php?m=file&f=download&t=txt&fileID=8",
            }})])
            page = Mock()
            with patch("zentao_skill.internal.zentao.files.LegacyWebClient", return_value=page):
                result = api.upload(file=file_path, object_type="bug", object_id=7)

        self.assertEqual(8, result["id"])
        page.upload_bug_attachment.assert_called_once()
        self.assertEqual(2, api._bugs.view.call_count)
        uploaded_fields = dict(page.upload_bug_attachment.call_args.kwargs["fields"])
        self.assertEqual("trunk", uploaded_fields["openedBuild[]"])
        self.assertNotIn("password", json.dumps(uploaded_fields))

    def test_matching_attachment_after_empty_v2_response_is_not_uploaded_again(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / "proof.txt"
            file_path.write_bytes(b"proof")
            session = Mock()
            session.post.side_effect = self._empty_v2_error()
            api = FilesAPI(session)
            api._bugs.view = Mock(return_value=self._detail({"8": {"id": 8, "title": "proof.txt", "size": 5}}))
            with patch("zentao_skill.internal.zentao.files.LegacyWebClient") as page_class:
                result = api.upload(file=file_path, object_type="bug", object_id=7)

        self.assertEqual(8, result["id"])
        page_class.assert_not_called()
        self.assertEqual(1, api._bugs.view.call_count)

    def test_uncertain_page_write_is_not_retried_when_readback_has_no_match(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / "proof.txt"
            file_path.write_bytes(b"proof")
            session = Mock()
            session.config = Config("http://127.0.0.1:1", "admin", "secret")
            session.post.side_effect = self._empty_v2_error()
            api = FilesAPI(session)
            api._bugs.view = Mock(side_effect=[self._detail({}), self._detail({})])
            page = Mock()
            page.upload_bug_attachment.side_effect = LegacyPageFailure(
                "connection lost", stage="upload", transport_uncertain=True
            )
            with patch("zentao_skill.internal.zentao.files.LegacyWebClient", return_value=page):
                with self.assertRaises(UnknownWriteResult):
                    api.upload(file=file_path, object_type="bug", object_id=7)
        page.upload_bug_attachment.assert_called_once()
        self.assertEqual(2, api._bugs.view.call_count)

    def test_non_bug_empty_v2_response_keeps_original_api_error(self) -> None:
        session = Mock()
        session.post.side_effect = self._empty_v2_error()
        api = FilesAPI(session)
        api._bugs.view = Mock()
        with self.assertRaises(ApiError):
            api.upload(file="/tmp/sample.txt", object_type="task", object_id=7)
        api._bugs.view.assert_not_called()


if __name__ == "__main__":
    unittest.main()
