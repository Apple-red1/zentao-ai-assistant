from __future__ import annotations

import http.client
import mimetypes
import socket
import uuid
from dataclasses import dataclass
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Iterable
from urllib import error, request
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

_MAX_PAGE_RESPONSE = 1024 * 1024


@dataclass(frozen=True)
class LegacyPageResponse:
    status: int
    url: str
    content_type: str
    body: bytes


@dataclass(frozen=True)
class LegacyForm:
    action: str | None
    hidden_fields: tuple[tuple[str, str], ...]


class LegacyPageFailure(Exception):
    """A page-protocol failure with no response body or credential material."""

    def __init__(
        self,
        message: str,
        *,
        stage: str,
        status: int | None = None,
        transport_uncertain: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.status = status
        self.transport_uncertain = transport_uncertain


class _SameOriginRedirectHandler(request.HTTPRedirectHandler):
    def __init__(self, origin: tuple[str, str, int]) -> None:
        super().__init__()
        self.origin = origin

    def redirect_request(
        self,
        req: request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> request.Request:
        if _origin(newurl) != self.origin:
            raise error.HTTPError(req.full_url, code, msg, headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.form_action: str | None = None
        self.hidden_fields: list[tuple[str, str]] = []
        self._in_form = False
        self._found_form = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs}
        normalized_tag = tag.lower()
        if normalized_tag == "form" and not self._found_form:
            self._found_form = True
            self._in_form = True
            self.form_action = attributes.get("action")
            return
        if normalized_tag != "input" or not self._in_form:
            return
        if (attributes.get("type") or "").lower() != "hidden":
            return
        name = attributes.get("name")
        if name:
            self.hidden_fields.append((name, attributes.get("value") or ""))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form" and self._in_form:
            self._in_form = False


class LegacyWebClient:
    """Small, same-origin client for ZenTao's legacy HTML form routes.

    This client is intentionally kept below the API/service layers. It only
    knows the page transport and cookie login; callers provide a fixed form
    route and must verify any write through the API afterwards.
    """

    def __init__(self, *, base_url: str, account: str, password: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.account = account
        self.password = password
        self.timeout = timeout
        self._origin = _origin(self.base_url)
        self._cookies = CookieJar()
        self._opener = request.build_opener(
            _SameOriginRedirectHandler(self._origin),
            request.HTTPCookieProcessor(self._cookies),
        )
        parsed = urlsplit(self.base_url)
        self._origin_header = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))

    def upload_bug_attachment(
        self,
        *,
        bug_id: int,
        fields: Iterable[tuple[str, object]],
        file: str | Path,
    ) -> LegacyPageResponse:
        login_url = self._page_url("/index.php?m=user&f=login")
        self._request("GET", login_url, headers=self._html_headers())

        # 21.7.8's web login checks the client-side password strength value,
        # although it is not rendered as a visible form control. Keep this
        # compatibility field in the direct request rather than using a
        # browser or a browser automation dependency.
        login_fields = (
            ("account", self.account),
            ("password", self.password),
            ("keepLogin", "on"),
            ("referer", login_url),
            ("passwordStrength", "3"),
        )
        login_response = self._request(
            "POST",
            login_url,
            headers=self._html_headers(referer=login_url, content_type="application/x-www-form-urlencoded; charset=UTF-8"),
            body=urlencode(login_fields, doseq=True).encode("utf-8"),
            stage="login",
        )
        if _looks_like_login_page(login_response):
            raise LegacyPageFailure("ZenTao 页面登录失败", stage="login", status=login_response.status)

        edit_url = self._page_url(f"/index.php?m=bug&f=edit&bugID={bug_id}")
        form_response = self._request(
            "GET",
            edit_url,
            headers=self._html_headers(referer=login_url),
            stage="form",
        )
        if _looks_like_login_page(form_response):
            raise LegacyPageFailure("ZenTao 页面会话未建立", stage="form", status=form_response.status)
        form = _parse_form(form_response.body)
        if form is None or not _is_bug_edit_form(form, edit_url):
            raise LegacyPageFailure("ZenTao Bug 编辑页面未返回可用表单", stage="form", status=form_response.status)

        supplied = list(fields)
        supplied_names = {name for name, _ in supplied}
        hidden = [(name, value) for name, value in form.hidden_fields if name not in supplied_names]
        payload_fields = [*hidden, *supplied, ("files[]", Path(file))]
        body, content_type = _encode_multipart(payload_fields)
        return self._request(
            "POST",
            edit_url,
            headers=self._html_headers(referer=edit_url, content_type=content_type),
            body=body,
            stage="upload",
        )

    def _page_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None = None,
        stage: str = "request",
    ) -> LegacyPageResponse:
        req = request.Request(url, data=body, method=method, headers=headers)
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                raw = response.read(_MAX_PAGE_RESPONSE + 1)
                if len(raw) > _MAX_PAGE_RESPONSE:
                    raw = raw[:_MAX_PAGE_RESPONSE]
                return LegacyPageResponse(
                    status=response.getcode(),
                    url=response.geturl(),
                    content_type=response.headers.get_content_type() or "",
                    body=raw,
                )
        except error.HTTPError as exc:
            # Do not include the HTML body: it may contain user-specific page
            # data and is not needed for the write/readback decision.
            try:
                exc.read(4096)
            except OSError:
                pass
            raise LegacyPageFailure(
                "ZenTao 页面请求返回错误",
                stage=stage,
                status=exc.code,
            ) from exc
        except error.URLError as exc:
            raise LegacyPageFailure(
                "ZenTao 页面请求网络失败",
                stage=stage,
                transport_uncertain=stage == "upload",
            ) from exc
        except (TimeoutError, socket.timeout, ConnectionResetError, BrokenPipeError,
                http.client.RemoteDisconnected, http.client.IncompleteRead) as exc:
            raise LegacyPageFailure(
                "ZenTao 页面请求网络失败",
                stage=stage,
                transport_uncertain=stage == "upload",
            ) from exc

    def _html_headers(self, *, referer: str | None = None, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "Origin": self._origin_header,
            "User-Agent": "zentao-ai-assistant/1.2",
        }
        if referer:
            headers["Referer"] = referer
        if content_type:
            headers["Content-Type"] = content_type
        return headers


def _origin(value: str) -> tuple[str, str, int]:
    parsed = urlsplit(value)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("页面 URL 不允许包含用户凭据")
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if scheme not in {"http", "https"} or not host:
        raise ValueError("页面 URL 必须使用 http/https")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("页面 URL 端口无效") from exc
    return scheme, host, port or (443 if scheme == "https" else 80)


def _looks_like_login_page(response: LegacyPageResponse) -> bool:
    text = response.body.decode("utf-8", errors="ignore").lower()
    return 'name="account"' in text and ('name="password"' in text or 'id="password"' in text)


def _parse_form(body: bytes) -> LegacyForm | None:
    parser = _FormParser()
    try:
        parser.feed(body.decode("utf-8", errors="replace"))
        parser.close()
    except Exception:
        return None
    if not parser._found_form:
        return None
    return LegacyForm(parser.form_action, tuple(parser.hidden_fields))


def _is_bug_edit_form(form: LegacyForm, expected_url: str) -> bool:
    if not form.action:
        return False
    try:
        action = urljoin(expected_url, form.action)
        if _origin(action) != _origin(expected_url):
            return False
    except ValueError:
        return False
    parsed = urlsplit(action)
    query = parse_qs(parsed.query)
    return (
        parsed.path == urlsplit(expected_url).path
        and query.get("m") == ["bug"]
        and query.get("f") == ["edit"]
    )


def _encode_multipart(values: Iterable[tuple[str, object]]) -> tuple[bytes, str]:
    boundary = f"----zentao-legacy-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in values:
        chunks.append(f"--{boundary}\r\n".encode("ascii"))
        if isinstance(value, Path):
            path = Path(value)
            filename = _header_filename(path.name)
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            chunks.append(
                f'Content-Disposition: form-data; name="{_header_filename(name)}"; filename="{filename}"\r\n'.encode("utf-8")
            )
            chunks.append(f"Content-Type: {mime}\r\n\r\n".encode("ascii"))
            chunks.append(path.read_bytes())
            chunks.append(b"\r\n")
            continue
        chunks.append(f'Content-Disposition: form-data; name="{_header_filename(name)}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _header_filename(value: str) -> str:
    return value.replace("\\", "_").replace('"', "_").replace("\r", "_").replace("\n", "_")
