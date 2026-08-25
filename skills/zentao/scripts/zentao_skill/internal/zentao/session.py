
from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

from ..config import Config
from ..errors import ApiError, HttpFailure, NetworkError, TransportFailure, UnknownWriteResult
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
                return self.http.request(
                    method,
                    url,
                    headers={"Token": self._token or ""},
                    json_body=body,
                    multipart=multipart,
                )
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
