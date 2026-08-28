
from __future__ import annotations

import json
import socket
import time
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .router import match
from .state import FakeState


class FakeZenTao:
    def __init__(self) -> None:
        self.state = FakeState()
        state = self.state

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None: self._handle()
            def do_POST(self) -> None: self._handle()
            def do_PUT(self) -> None: self._handle()
            def do_DELETE(self) -> None: self._handle()

            def _handle(self) -> None:
                split = urlsplit(self.path)
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
                        self.send_header("Content-Disposition", f'attachment; filename="{item["filename"]}"')
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
