
from __future__ import annotations

import json
import socket
import time
from email import policy
from email.parser import BytesParser
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from zentao_skill.comment_contract import canonical_object_type
from .router import match
from .state import FakeState


class FakeZenTao:
    def __init__(self) -> None:
        self.state = FakeState()
        state = self.state

        class Handler(BaseHTTPRequestHandler):
            _DETAIL_MODULES = {
                "bug": "bug",
                "story": "story",
                "product": "product",
                "task": "task",
                "execution": "execution",
                "project": "project",
                "testtask": "test-task",
                "productplan": "product-plan",
                "release": "release",
                "build": "build",
            }

            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None: self._handle()
            def do_POST(self) -> None: self._handle()
            def do_PUT(self) -> None: self._handle()
            def do_DELETE(self) -> None: self._handle()

            def _handle(self) -> None:
                split = urlsplit(self.path)
                if split.path == "/index.php" and self._handle_legacy(split):
                    return
                if self.command == "GET" and (split.path in state.binary_resources or split.path in state.redirects):
                    if self.headers.get("Token") != "fake-token":
                        self._send(401, {"error": "invalid token"}); return
                    query = {k: (v if len(v) > 1 else v[0]) for k, v in parse_qs(split.query).items()}
                    state.record({"endpoint_id": "resource.binary", "method": self.command, "path": split.path, "query": query, "body": {}})
                    if split.path in state.redirects:
                        self.send_response(302)
                        self.send_header("Location", state.redirects[split.path])
                        self.end_headers()
                        return
                    item = state.binary_resources[split.path]
                    raw = item["content"]
                    self.send_response(200)
                    self.send_header("Content-Type", str(item["content_type"]))
                    self.send_header("Content-Length", str(len(raw)))
                    if item.get("filename"):
                        filename = str(item["filename"])
                        try:
                            filename.encode("latin-1")
                            disposition = f'attachment; filename="{filename}"'
                        except UnicodeEncodeError:
                            disposition = f"attachment; filename=download; filename*=UTF-8''{quote(filename)}"
                        self.send_header("Content-Disposition", disposition)
                    self.end_headers()
                    try:
                        self.wfile.write(raw)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    return
                matched = match(self.command, split.path)
                if matched is None:
                    self._send(404, {"error": "unknown endpoint"}); return
                route, path_params = matched
                if route.endpoint_id != "token.login" and self.headers.get("Token") != "fake-token":
                    self._send(401, {"error": "invalid token"}); return
                query = {k: (v if len(v) > 1 else v[0]) for k, v in parse_qs(split.query).items()}
                body = self._read_body()
                state.record({"endpoint_id": route.endpoint_id, "method": self.command, "path": split.path, "path_params": path_params, "query": query, "body": body})
                fault = state.next_fault(route.endpoint_id)
                if fault in {"400","401","403","404","422","500","502","503","504"}:
                    self._send(int(fault), {"error": f"injected {fault}"}); return
                if fault == "status_fail":
                    self._send(200, {"status": "fail", "message": "injected business failure"}); return
                if fault == "empty":
                    self._send(200, None); return
                if fault == "success_missing_id":
                    self._send(200, {"status": "success"}); return
                if fault == "success_missing_collection":
                    self._send(200, {"status": "success"}); return
                if fault == "timeout":
                    time.sleep(0.5)
                if fault == "drop":
                    self._drop(); return
                error_payload = self._validate_contract(route, query, body)
                if error_payload is not None:
                    self._send(400, error_payload); return
                status, payload = state.handle(route, path_params, query, body)
                if fault == "commit_then_drop":
                    self._drop(); return
                if fault == "malformed_json":
                    self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b"{broken"); return
                self._send(status, payload)

            def _handle_legacy(self, split: object) -> bool:
                query = {k: (v if len(v) > 1 else v[0]) for k, v in parse_qs(split.query).items()}
                module = str(query.get("m") or "")
                function = str(query.get("f") or "")
                if module == "user" and function == "login":
                    self._handle_login(query)
                    return True
                if module == "action" and function == "comment":
                    self._handle_comment(query)
                    return True
                if module == "file" and function == "ajaxUpload":
                    self._handle_inline_upload(query)
                    return True
                if module in self._DETAIL_MODULES and function == "view":
                    self._handle_detail_page(module, query)
                    return True
                # file/download and file/read are handled by the binary route
                # below so resource security and content checks stay intact.
                return False

            def _handle_login(self, query: dict[str, Any]) -> None:
                if self.command == "GET":
                    state.record({"endpoint_id": "web.login.form", "method": self.command, "path": "/index.php", "query": query, "body": {}})
                    self._send_raw(
                        200,
                        b'<html><form method="post"><input name="account"><input name="password" type="password"></form></html>',
                        "text/html",
                    )
                    return
                raw = self._read_raw()
                values = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
                body = {key: items[-1] if items else "" for key, items in values.items()}
                state.record({"endpoint_id": "web.login", "method": self.command, "path": "/index.php", "query": query, "body": {"account": body.get("account", "")}})
                if not body.get("account") or not body.get("password"):
                    self._send_raw(401, b'<html><input name="account"><input name="password"></html>', "text/html")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Set-Cookie", "zentaosid=fake-session; Path=/; HttpOnly")
                self.end_headers()
                self.wfile.write(b"<html><body>dashboard</body></html>")

            def _handle_comment(self, query: dict[str, Any]) -> None:
                if not self._authenticated():
                    self._send_raw(401, b"<html>login required</html>", "text/html")
                    return
                object_type = canonical_object_type(query.get("objectType"))
                try:
                    object_id = int(query.get("objectID"))
                except (TypeError, ValueError):
                    self._send_raw(400, b"<html>invalid object</html>", "text/html")
                    return
                if self.command == "GET":
                    state.record({"endpoint_id": "web.comment.form", "method": self.command, "path": "/index.php", "query": query, "body": {}})
                    fault = state.next_web_fault("comment_form")
                    if self._handle_web_fault(fault):
                        return
                    uid = f"fake-uid-{object_type}-{object_id}"
                    body = (
                        f'<html><form action="/index.php?m=action&amp;f=comment&amp;objectType={escape(object_type)}&amp;objectID={object_id}" method="post">'
                        f'<input type="hidden" name="uid" value="{escape(uid)}">'
                        f'<textarea name="actioncomment"></textarea></form></html>'
                    ).encode("utf-8")
                    self._send_raw(200, body, "text/html")
                    return

                body = self._read_legacy_multipart()
                files = body.get("files[]", [])
                file_entries = files if isinstance(files, list) else []
                state.record({
                    "endpoint_id": "web.comment",
                    "method": self.command,
                    "path": "/index.php",
                    "query": query,
                    "body": {
                        "uid": body.get("uid"),
                        "actioncomment": body.get("actioncomment"),
                        "files[]": [{"name": item.get("name"), "size": len(item.get("content", b""))} for item in file_entries if isinstance(item, dict)],
                    },
                })
                fault = state.next_web_fault("comment")
                if self._handle_web_fault(fault):
                    return
                if fault in {"200_no_persist", "status_fail"}:
                    self._send_raw(200, b"<html><body>comment failed</body></html>", "text/html")
                    return
                normalized_files = [
                    {
                        "name": str(item.get("name") or "upload.bin"),
                        "content": bytes(item.get("content") or b""),
                        "content_type": str(item.get("content_type") or "application/octet-stream"),
                    }
                    for item in file_entries
                    if isinstance(item, dict)
                ]
                state.add_comment(
                    resource=object_type,
                    object_id=object_id,
                    comment=str(body.get("actioncomment") or ""),
                    files=normalized_files,
                )
                if fault in {"commit_then_drop", "drop_after_commit"}:
                    self._drop()
                    return
                self._send_raw(200, b"<html><body>comment saved</body></html>", "text/html")

            def _handle_inline_upload(self, query: dict[str, Any]) -> None:
                if not self._authenticated():
                    self._send_raw(401, b"<html>login required</html>", "text/html")
                    return
                body = self._read_legacy_multipart()
                image = body.get("imgFile")
                image_entry = image[0] if isinstance(image, list) and image else None
                if not isinstance(image_entry, dict):
                    self._send_raw(400, b"<html>missing imgFile</html>", "text/html")
                    return
                state.record({
                    "endpoint_id": "web.inline_upload",
                    "method": self.command,
                    "path": "/index.php",
                    "query": query,
                    "body": {"uid": query.get("uid"), "file": {"name": image_entry.get("name"), "size": len(image_entry.get("content", b""))}},
                })
                fault = state.next_web_fault("inline_upload")
                if fault == "malformed":
                    self._send_raw(200, b"{}", "application/json")
                    return
                if self._handle_web_fault(fault):
                    return
                file_id, url = state.add_inline_image(
                    bytes(image_entry.get("content") or b""),
                    filename=str(image_entry.get("name") or "inline.png"),
                    content_type=str(image_entry.get("content_type") or "image/png"),
                )
                if fault in {"commit_then_drop", "drop_after_commit"}:
                    self._drop()
                    return
                self._send_json_raw(200, {"fileID": file_id, "url": url})

            def _handle_detail_page(self, module: str, query: dict[str, Any]) -> None:
                if not self._authenticated():
                    self._send_raw(401, b"<html>login required</html>", "text/html")
                    return
                object_type = self._DETAIL_MODULES[module]
                id_value = next((value for key, value in query.items() if key.lower().endswith("id")), None)
                try:
                    object_id = int(id_value)
                except (TypeError, ValueError):
                    self._send_raw(400, b"<html>invalid object</html>", "text/html")
                    return
                state.record({"endpoint_id": "web.object.detail", "method": self.command, "path": "/index.php", "query": query, "body": {}})
                fault = state.next_web_fault("detail")
                if self._handle_web_fault(fault):
                    return
                item = state.resources.get(object_type, {}).get(str(object_id))
                if not isinstance(item, dict):
                    self._send_raw(404, b"<html>not found</html>", "text/html")
                    return
                critical_html = "".join(
                    f'<div data-field="{escape(str(key))}" data-value="{escape(str(item[key]))}"></div>'
                    for key in ("status", "title", "name", "product", "project", "execution", "model")
                    if key in item
                )
                action_json = json.dumps({"actions": item.get("actions", [])}, ensure_ascii=False)
                body = (
                    f"<html><body>{critical_html}<script type=\"application/json\">{action_json}</script></body></html>"
                ).encode("utf-8")
                self._send_raw(200, body, "text/html")

            def _authenticated(self) -> bool:
                return "zentaosid=fake-session" in (self.headers.get("Cookie") or "")

            def _handle_web_fault(self, fault: str | None) -> bool:
                if fault in {"400", "401", "403", "404", "422", "500", "502", "503", "504"}:
                    self._send_raw(int(fault), b"<html>injected web failure</html>", "text/html")
                    return True
                if fault == "drop":
                    self._drop()
                    return True
                return False

            def _validate_contract(self, route: object, query: dict[str, Any], body: dict[str, Any]) -> dict[str, Any] | None:
                missing_query=[name for name in route.required_query if name not in query]
                missing_body=[name for name in route.required_body if name not in body]
                if missing_query or missing_body:
                    return {"error": "missing required fields", "query": missing_query, "body": missing_body}
                for name, allowed in route.enum_values:
                    value=body.get(name, query.get(name))
                    if value is None:
                        continue
                    values=value if isinstance(value, list) else [value]
                    if any(str(item) not in allowed for item in values):
                        return {"error": "invalid enum", "field": name}
                return None

            def _read_body(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length else b""
                ctype = self.headers.get("Content-Type", "")
                if not raw: return {}
                if ctype.startswith("application/json"):
                    return json.loads(raw.decode("utf-8"))
                if ctype.startswith("multipart/form-data"):
                    message = BytesParser(policy=policy.default).parsebytes(
                        ("Content-Type: " + ctype + "\r\nMIME-Version: 1.0\r\n\r\n").encode() + raw
                    )
                    values: dict[str, Any] = {}
                    for part in message.iter_parts():
                        name = part.get_param("name", header="content-disposition")
                        filename = part.get_filename()
                        if not name: continue
                        values[name] = filename if filename else part.get_content().strip()
                    return values
                return {"raw": raw.decode("utf-8", errors="replace")}

            def _read_raw(self) -> bytes:
                length = int(self.headers.get("Content-Length", "0") or 0)
                return self.rfile.read(length) if length else b""

            def _read_legacy_multipart(self) -> dict[str, Any]:
                raw = self._read_raw()
                ctype = self.headers.get("Content-Type", "")
                message = BytesParser(policy=policy.default).parsebytes(
                    ("Content-Type: " + ctype + "\r\nMIME-Version: 1.0\r\n\r\n").encode() + raw
                )
                values: dict[str, Any] = {}
                for part in message.iter_parts():
                    name = part.get_param("name", header="content-disposition")
                    if not name:
                        continue
                    content = part.get_payload(decode=True) or b""
                    filename = part.get_filename()
                    if filename:
                        values.setdefault(name, []).append({
                            "name": filename,
                            "content": content,
                            "content_type": part.get_content_type(),
                        })
                    else:
                        values[name] = content.decode("utf-8", errors="replace")
                return values

            def _drop(self) -> None:
                try: self.connection.shutdown(socket.SHUT_RDWR)
                except OSError: pass
                self.connection.close()

            def _send(self, status: int, payload: object | None) -> None:
                self.send_response(status)
                if payload is not None:
                    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                if payload is not None:
                    try:
                        self.wfile.write(raw)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

            def _send_raw(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def _send_json_raw(self, status: int, payload: object) -> None:
                self._send_raw(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json")

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=lambda: self.httpd.serve_forever(poll_interval=0.01), daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "FakeZenTao":
        self.thread.start(); return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.httpd.shutdown(); self.httpd.server_close(); self.thread.join(timeout=2)
