
from __future__ import annotations

from ..errors import ApiError, HttpFailure, NetworkError, TransportFailure
from ..http.client import HttpClient
from .common import endpoint


class AuthAPI:
    ENDPOINT_IDS = frozenset({"token.login"})

    def __init__(self, base_url: str, http: HttpClient) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http

    @endpoint("token.login")
    def login(self, *, account: str, password: str) -> str:
        try:
            result = self.http.request(
                "POST",
                self.base_url + "/api.php/v2/users/login",
                json_body={"account": account, "password": password},
            )
        except HttpFailure as exc:
            raise ApiError("ZenTao 登录失败", {"status": exc.status, "response": exc.body}) from exc
        except TransportFailure as exc:
            raise NetworkError("无法连接 ZenTao 登录接口") from exc
        if not isinstance(result, dict) or not isinstance(result.get("token"), str) or not result["token"]:
            raise ApiError("ZenTao 登录响应缺少有效 token")
        return result["token"]
