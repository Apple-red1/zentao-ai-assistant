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
from zentao_skill.internal.http.legacy import LegacyPageFailure, LegacyPageResponse, LegacyWebClient
from zentao_skill.internal.zentao.files import FilesAPI


class LegacyUploadPageTests(unittest.TestCase):
    def test_login_html_after_login_is_a_failure_without_comment_request(self) -> None:
        client = LegacyWebClient(base_url="http://127.0.0.1:1", account="admin", password="secret")
        client._request = Mock(side_effect=[
            LegacyPageResponse(200, "http://127.0.0.1:1/index.php?m=user&f=login", "text/html", b'<form><input name="account"><input name="password"></form>'),
            LegacyPageResponse(200, "http://127.0.0.1:1/index.php?m=user&f=login", "text/html", b'<form><input name="account"><input name="password"></form>'),
        ])

        with self.assertRaises(LegacyPageFailure) as raised:
            client.get_comment_form(object_type="bug", object_id=7)

        self.assertEqual("login", raised.exception.stage)
        self.assertNotIn("secret", str(raised.exception))
        self.assertEqual(2, client._request.call_count)

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

    def test_page_client_fetches_comment_form_and_posts_repeatable_files(self) -> None:
        state: dict[str, object] = {
            "comment_get": None,
            "comment_fields": {},
            "file_parts": [],
        }

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                split = urlsplit(self.path)
                query = parse_qs(split.query)
                if split.path != "/index.php":
                    self._send(404, "not found")
                    return
                if query.get("m") == ["user"] and query.get("f") == ["login"]:
                    self._send(200, '<form><input name="account"><input name="password"></form>', cookie="sid=login; Path=/")
                    return
                if query.get("m") == ["action"] and query.get("f") == ["comment"]:
                    state["comment_get"] = query
                    self._send(
                        200,
                        '<form action="/index.php?m=action&amp;f=comment" method="post">'
                        '<input type="hidden" name="uid" value="server-uid">'
                        '<textarea name="actioncomment"></textarea></form>',
                    )
                    return
                self._send(404, "not found")

            def do_POST(self) -> None:
                split = urlsplit(self.path)
                query = parse_qs(split.query)
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length)
                if query.get("m") == ["user"] and query.get("f") == ["login"]:
                    self._send(200, "<html>home</html>", cookie="auth=ok; Path=/")
                    return
                if query.get("m") == ["action"] and query.get("f") == ["comment"]:
                    self.assert_authenticated()
                    message = BytesParser(policy=default).parsebytes(
                        ("Content-Type: " + self.headers.get("Content-Type", "") + "\r\n"
                         "MIME-Version: 1.0\r\n\r\n").encode() + raw
                    )
                    fields: dict[str, list[str]] = {}
                    files: list[tuple[str, bytes]] = []
                    for part in message.iter_parts():
                        name = part.get_param("name", header="content-disposition")
                        if not name:
                            continue
                        filename = part.get_filename()
                        if filename:
                            files.append((filename, part.get_payload(decode=True) or b""))
                        else:
                            fields.setdefault(name, []).append(part.get_content())
                    state["comment_fields"] = fields
                    state["file_parts"] = files
                    self._send(200, "<html>saved</html>")
                    return
                self._send(404, "not found")

            def assert_authenticated(self) -> None:
                if "auth=ok" not in self.headers.get("Cookie", ""):
                    self._send(403, "not authenticated")
                    raise AssertionError("missing page session")

            def _send(self, status: int, body: str, *, cookie: str | None = None) -> None:
                raw = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html")
                if cookie:
                    self.send_header("Set-Cookie", cookie)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                first = Path(td) / "first.txt"
                second = Path(td) / "第二.bin"
                first.write_bytes(b"first")
                second.write_bytes(b"second")
                client = LegacyWebClient(
                    base_url=f"http://127.0.0.1:{server.server_address[1]}",
                    account="admin",
                    password="secret",
                )
                form = client.get_comment_form(object_type="bug", object_id=7)
                response = client.post_comment(
                    object_type="bug",
                    object_id=7,
                    uid="server-uid",
                    actioncomment="comment body",
                    files=(first, second),
                )
            self.assertEqual(200, form.status)
            self.assertEqual({"m": ["action"], "f": ["comment"], "objectType": ["bug"], "objectID": ["7"]}, state["comment_get"])
            self.assertEqual(200, response.status)
            self.assertEqual(["server-uid"], state["comment_fields"]["uid"])
            self.assertEqual(["comment body"], state["comment_fields"]["actioncomment"])
            self.assertEqual(
                [("first.txt", b"first"), ("第二.bin", b"second")],
                state["file_parts"],
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_page_client_posts_inline_image_to_fixed_ajax_upload_route(self) -> None:
        state: dict[str, object] = {"query": None, "file_name": None, "file_bytes": b""}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                split = urlsplit(self.path)
                query = parse_qs(split.query)
                if split.path == "/index.php" and query.get("m") == ["user"] and query.get("f") == ["login"]:
                    self._send(200, '<form><input name="account"><input name="password"></form>')
                    return
                self._send(404, "not found")

            def do_POST(self) -> None:
                split = urlsplit(self.path)
                query = parse_qs(split.query)
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length)
                if query.get("m") == ["user"] and query.get("f") == ["login"]:
                    self._send(200, "<html>home</html>", cookie="auth=ok; Path=/")
                    return
                if query.get("m") == ["file"] and query.get("f") == ["ajaxUpload"]:
                    self.assert_authenticated()
                    state["query"] = query
                    message = BytesParser(policy=default).parsebytes(
                        ("Content-Type: " + self.headers.get("Content-Type", "") + "\r\n"
                         "MIME-Version: 1.0\r\n\r\n").encode() + raw
                    )
                    for part in message.iter_parts():
                        if part.get_param("name", header="content-disposition") == "imgFile":
                            state["file_name"] = part.get_filename()
                            state["file_bytes"] = part.get_payload(decode=True) or b""
                    self._send(200, '{"fileID": 12, "url": "/file/12.png"}')
                    return
                self._send(404, "not found")

            def assert_authenticated(self) -> None:
                if "auth=ok" not in self.headers.get("Cookie", ""):
                    self._send(403, "not authenticated")
                    raise AssertionError("missing page session")

            def _send(self, status: int, body: str, *, cookie: str | None = None) -> None:
                raw = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html")
                if cookie:
                    self.send_header("Set-Cookie", cookie)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                image = Path(td) / "inline.png"
                image.write_bytes(b"png-payload")
                client = LegacyWebClient(
                    base_url=f"http://127.0.0.1:{server.server_address[1]}",
                    account="admin",
                    password="secret",
                )
                response = client.upload_inline_image(
                    object_type="bug",
                    object_id=7,
                    uid="server-uid",
                    file=image,
                )
            self.assertEqual(200, response.status)
            self.assertEqual({"m": ["file"], "f": ["ajaxUpload"], "uid": ["server-uid"]}, state["query"])
            self.assertEqual("inline.png", state["file_name"])
            self.assertEqual(b"png-payload", state["file_bytes"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_cross_origin_comment_redirect_does_not_send_cookie_or_body(self) -> None:
        target_state: dict[str, object] = {"requests": 0, "cookie": None, "body": b""}

        class TargetHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_POST(self) -> None:
                target_state["requests"] = int(target_state["requests"]) + 1
                length = int(self.headers.get("Content-Length", "0") or 0)
                target_state["cookie"] = self.headers.get("Cookie")
                target_state["body"] = self.rfile.read(length)
                self.send_response(200)
                self.end_headers()

        target = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
        target.daemon_threads = True
        target_thread = Thread(target=lambda: target.serve_forever(poll_interval=0.01), daemon=True)
        target_thread.start()

        class OriginHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                split = urlsplit(self.path)
                query = parse_qs(split.query)
                if split.path == "/index.php" and query.get("m") == ["user"] and query.get("f") == ["login"]:
                    self._send(200, '<form><input name="account"><input name="password"></form>')
                    return
                self._send(404, "not found")

            def do_POST(self) -> None:
                split = urlsplit(self.path)
                query = parse_qs(split.query)
                length = int(self.headers.get("Content-Length", "0") or 0)
                self.rfile.read(length)
                if query.get("m") == ["user"] and query.get("f") == ["login"]:
                    self._send(200, "<html>home</html>", cookie="auth=ok; Path=/")
                    return
                if query.get("m") == ["action"] and query.get("f") == ["comment"]:
                    self.send_response(302)
                    self.send_header("Location", f"http://127.0.0.1:{target.server_address[1]}/stolen")
                    self.end_headers()
                    return
                self._send(404, "not found")

            def _send(self, status: int, body: str, *, cookie: str | None = None) -> None:
                raw = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html")
                if cookie:
                    self.send_header("Set-Cookie", cookie)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        origin = ThreadingHTTPServer(("127.0.0.1", 0), OriginHandler)
        origin.daemon_threads = True
        origin_thread = Thread(target=lambda: origin.serve_forever(poll_interval=0.01), daemon=True)
        origin_thread.start()
        try:
            client = LegacyWebClient(
                base_url=f"http://127.0.0.1:{origin.server_address[1]}",
                account="admin",
                password="secret",
            )
            with self.assertRaises(LegacyPageFailure):
                client.post_comment(
                    object_type="bug",
                    object_id=7,
                    uid="server-uid",
                    actioncomment="comment body",
                )
            self.assertEqual(0, target_state["requests"])
        finally:
            origin.shutdown()
            origin.server_close()
            origin_thread.join(timeout=2)
            target.shutdown()
            target.server_close()
            target_thread.join(timeout=2)


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
