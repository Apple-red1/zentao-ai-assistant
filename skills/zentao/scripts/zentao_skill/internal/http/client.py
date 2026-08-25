from __future__ import annotations

import http.client
import json
import mimetypes
import socket
import ssl
import uuid
from pathlib import Path
from typing import Any
from urllib import error, request

from ..errors import HttpFailure, MalformedResponse, TransportFailure


class _RejectRedirectHandler(request.HTTPRedirectHandler):
    """Keep API calls on their explicitly selected URL.

    ``urllib`` otherwise follows Location automatically and may rewrite a
    POST/PUT to GET while carrying authentication headers to another origin.
    Raising ``HTTPError`` here lets the normal status mapping handle the 3xx
    response without making a second request.
    """

    def redirect_request(self, req: request.Request, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> request.Request:
        raise error.HTTPError(req.full_url, code, msg, headers, fp)

class _NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> request.Request | None:
        return None


class HttpClient:
    def __init__(self, *, timeout: float = 10.0) -> None:
        self.timeout = timeout
        self._opener = request.build_opener(_RejectRedirectHandler())
        self._download_opener = request.build_opener(_NoRedirectHandler())

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        multipart: dict[str, Any] | None = None,
    ) -> object | None:
        final_headers = dict(headers or {})
        data: bytes | None = None
        if json_body is not None and multipart is not None:
            raise ValueError("json_body 与 multipart 不能同时存在")
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            final_headers["Content-Type"] = "application/json"
        elif multipart is not None:
            data, content_type = self._encode_multipart(multipart)
            final_headers["Content-Type"] = content_type
        req = request.Request(url, data=data, method=method, headers=final_headers)
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                raw = response.read()
                if not raw:
                    return None
                try:
                    return json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise MalformedResponse() from exc
        except error.HTTPError as exc:
            raise self._http_failure(exc) from exc
        except error.URLError as exc:
            raise self._transport_failure(exc) from exc
        except (TimeoutError, socket.timeout, ConnectionResetError, BrokenPipeError,
                http.client.RemoteDisconnected, http.client.IncompleteRead) as exc:
            raise TransportFailure(str(exc), definitely_not_sent=False) from exc

    def download(
        self,
        url: str,
        destination: str | Path,
        *,
        headers: dict[str, str] | None = None,
        chunk_size: int = 64 * 1024,
    ) -> dict[str, object]:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        req = request.Request(url, method="GET", headers=dict(headers or {}))
        try:
            with self._download_opener.open(req, timeout=self.timeout) as response:
                total = 0
                with path.open("wb") as stream:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        stream.write(chunk)
                        total += len(chunk)
                return {
                    "url": response.geturl(),
                    "content_type": response.headers.get_content_type() or "application/octet-stream",
                    "content_disposition": response.headers.get("Content-Disposition"),
                    "size": total,
                }
        except error.HTTPError as exc:
            path.unlink(missing_ok=True)
            raise self._http_failure(exc, limit=4096) from exc
        except error.URLError as exc:
            path.unlink(missing_ok=True)
            raise self._transport_failure(exc) from exc
        except (TimeoutError, socket.timeout, ConnectionResetError, BrokenPipeError,
                http.client.RemoteDisconnected, http.client.IncompleteRead) as exc:
            path.unlink(missing_ok=True)
            raise TransportFailure(str(exc), definitely_not_sent=False) from exc
        except OSError:
            path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _http_failure(exc: error.HTTPError, *, limit: int | None = None) -> HttpFailure:
        raw = exc.read() if limit is None else exc.read(limit)
        body: object | None = None
        if raw:
            try:
                body = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                body = {"message": raw.decode("utf-8", errors="replace")[:500]}
        headers = {str(key): str(value) for key, value in exc.headers.items()} if exc.headers else {}
        return HttpFailure(exc.code, body, headers=headers)

    @staticmethod
    def _transport_failure(exc: error.URLError) -> TransportFailure:
        reason = exc.reason
        definitely_not_sent = isinstance(reason, (ConnectionRefusedError, socket.gaierror, ssl.SSLError))
        if isinstance(reason, (TimeoutError, socket.timeout, ConnectionResetError)):
            definitely_not_sent = False
        return TransportFailure(str(reason), definitely_not_sent=definitely_not_sent)

    @staticmethod
    def _encode_multipart(values: dict[str, Any]) -> tuple[bytes, str]:
        boundary = f"----zentao-{uuid.uuid4().hex}"
        chunks: list[bytes] = []
        for name, value in values.items():
            if value is None:
                continue
            chunks.append(f"--{boundary}\r\n".encode())
            if name == "file":
                path = Path(value)
                if not path.is_file():
                    raise FileNotFoundError(path)
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                chunks.append(
                    f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode("utf-8")
                )
                chunks.append(f"Content-Type: {mime}\r\n\r\n".encode())
                chunks.append(path.read_bytes())
                chunks.append(b"\r\n")
            else:
                chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
                chunks.append(str(value).encode("utf-8"))
                chunks.append(b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode())
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
