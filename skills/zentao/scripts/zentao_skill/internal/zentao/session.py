
from __future__ import annotations

import time
from typing import Any
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from ..config import Config
from ..errors import ApiError, HttpFailure, NetworkError, ResourceSecurityError, TransportFailure, UnknownWriteResult
from ..http.client import HttpClient
from .auth import AuthAPI


class ZentaoSession:
    def __init__(self, config: Config, *, http: HttpClient | None = None, retry_delays: tuple[float, float] = (0.2, 0.5)) -> None:
        self.config = config
        self.http = http or HttpClient()
        self.auth = AuthAPI(config.base_url, self.http)
        self.retry_delays = retry_delays
        self._token: str | None = None

    def ensure_login(self) -> None:
        if self._token is None:
            self._token = self.auth.login(account=self.config.account, password=self.config.password)

    def get(self, path: str, *, query: dict[str, Any] | None = None) -> object | None:
        return self._request("GET", path, query=query)

    def post(self, path: str, *, body: dict[str, Any] | None = None, multipart: dict[str, Any] | None = None) -> object | None:
        return self._request("POST", path, body=body, multipart=multipart)

    def put(self, path: str, *, body: dict[str, Any] | None = None) -> object | None:
        return self._request("PUT", path, body=body)

    def delete(self, path: str) -> object | None:
        return self._request("DELETE", path)

    def download_resource(self, source: str, destination: str | Path) -> dict[str, object]:
        self.ensure_login()
        current = self._resolve_trusted_resource_url(source)
        attempts = 3
        redirects = 0
        while True:
            for attempt in range(attempts):
                try:
                    return self.http.download(
                        current,
                        destination,
                        headers={"Token": self._token or ""},
                    )
                except HttpFailure as exc:
                    if exc.status in {301, 302, 303, 307, 308}:
                        location = exc.headers.get("Location") or exc.headers.get("location")
                        if not location:
                            raise ApiError("ZenTao 资源重定向缺少 Location", {"status": exc.status}) from exc
                        redirects += 1
                        if redirects > 5:
                            raise ApiError("ZenTao 资源重定向次数过多", {"status": exc.status}) from exc
                        current = self._resolve_trusted_resource_url(urljoin(current, location))
                        break
                    if exc.status in {502, 503, 504} and attempt < attempts - 1:
                        time.sleep(self.retry_delays[attempt])
                        continue
                    raise ApiError("ZenTao 资源下载返回错误", {"status": exc.status, "response": exc.body}) from exc
                except TransportFailure as exc:
                    if attempt < attempts - 1:
                        time.sleep(self.retry_delays[attempt])
                        continue
                    raise NetworkError("ZenTao 资源下载网络请求失败") from exc
            else:
                raise NetworkError("ZenTao 资源下载重试后仍失败")
            continue

    def _resolve_trusted_resource_url(self, source: str) -> str:
        base = self.config.base_url.rstrip("/") + "/"
        resolved = urljoin(base, source)
        parsed = urlsplit(resolved)
        if parsed.username is not None or parsed.password is not None:
            raise ResourceSecurityError("资源 URL 不允许包含用户凭据", {"source": source})
        if self._origin(resolved) != self._origin(self.config.base_url):
            raise ResourceSecurityError("资源 URL 超出当前 ZenTao 站点可信范围", {"source": source})
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))

    @staticmethod
    def _origin(url: str) -> tuple[str, str, int]:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").lower()
        if scheme not in {"http", "https"} or not host:
            raise ResourceSecurityError("资源 URL 必须使用 http/https", {"source": url})
        try:
            port = parsed.port
        except ValueError as exc:
            raise ResourceSecurityError("资源 URL 端口无效", {"source": url}) from exc
        return scheme, host, port or (443 if scheme == "https" else 80)

    def _request(self, method: str, path: str, *, query: dict[str, Any] | None = None,
                 body: dict[str, Any] | None = None, multipart: dict[str, Any] | None = None) -> object | None:
        self.ensure_login()
        url = self.config.base_url.rstrip("/") + "/api.php/v2" + path
        if query:
            encoded = urlencode(query, doseq=True)
            if encoded:
                url += "?" + encoded
        attempts = 3 if method == "GET" else 1
        for attempt in range(attempts):
            try:
                result = self.http.request(
                    method,
                    url,
                    headers={"Token": self._token or ""},
                    json_body=body,
                    multipart=multipart,
                )
                if isinstance(result, dict) and (
                    result.get("status") == "fail" or result.get("result") == "fail"
                ):
                    raise ApiError(
                        "ZenTao API 业务处理失败",
                        {"method": method, "path": path, "response": result},
                    )
                if result is None and method != "DELETE":
                    raise ApiError(
                        "ZenTao API 返回空响应",
                        {"method": method, "path": path, "response": None},
                    )
                return result
            except HttpFailure as exc:
                if method == "GET" and exc.status in {502, 503, 504} and attempt < attempts - 1:
                    time.sleep(self.retry_delays[attempt])
                    continue
                raise ApiError("ZenTao API 返回错误", {"status": exc.status, "response": exc.body}) from exc
            except TransportFailure as exc:
                if method == "GET" and attempt < attempts - 1:
                    time.sleep(self.retry_delays[attempt])
                    continue
                if method == "GET" or exc.definitely_not_sent:
                    raise NetworkError("ZenTao 网络请求失败") from exc
                raise UnknownWriteResult() from exc
        raise NetworkError("ZenTao 读取请求重试后仍失败")
