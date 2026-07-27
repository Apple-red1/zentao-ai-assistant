from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

import httpx

from zentao_ai.auth import AuthManager
from zentao_ai.credentials import CredentialStore, normalize_base_url
from zentao_ai.errors import ErrorCode, ZentaoError
from zentao_ai.models import Settings

Sleep = Callable[[float], Awaitable[None]]


class ZentaoClient:
    def __init__(
        self,
        settings: Settings,
        credentials: CredentialStore,
        *,
        http_client: httpx.AsyncClient | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._base_url = normalize_base_url(str(settings.zentao.base_url))
        self._api_root = f"{self._base_url}/api.php/{settings.zentao.api_version}"
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0),
            follow_redirects=False,
        )
        self._auth = AuthManager(settings, credentials, self._http)
        self._sleep = sleep

    async def __aenter__(self) -> ZentaoClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    def _url(self, path: str) -> str:
        parsed = urlsplit(path)
        if (
            not path.startswith("/")
            or parsed.scheme
            or parsed.netloc
            or any(part == ".." for part in parsed.path.split("/"))
        ):
            raise ZentaoError(
                ErrorCode.VALIDATION_ERROR,
                "API path must be a same-origin absolute path.",
            )
        return f"{self._api_root}{path}"

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        json: Mapping[str, object] | None = None,
        write: bool = False,
    ) -> dict[str, Any]:
        url = self._url(path)
        token = await self._auth.get_token()
        auth_replayed = False
        retry_count = 0
        backoffs = (0.2, 0.5)

        while True:
            try:
                response = await self._http.request(
                    method.upper(),
                    url,
                    params=params,
                    json=json,
                    headers={"Accept": "application/json", "Token": token},
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if write:
                    raise ZentaoError(
                        ErrorCode.UNKNOWN_WRITE_RESULT,
                        "The write result is unknown because the connection ended before "
                        "confirmation.",
                    ) from exc
                if retry_count < len(backoffs):
                    await self._sleep(backoffs[retry_count])
                    retry_count += 1
                    continue
                raise ZentaoError(
                    ErrorCode.NETWORK_ERROR,
                    "Unable to reach ZenTao after retrying.",
                    retryable=True,
                ) from exc

            if response.status_code == 401:
                if auth_replayed:
                    raise ZentaoError(
                        ErrorCode.AUTH_ERROR,
                        "ZenTao rejected the refreshed login token.",
                    )
                token = await self._auth.refresh_after_unauthorized(token)
                auth_replayed = True
                continue

            if (
                not write
                and response.status_code in {429, 500, 502, 503, 504}
                and retry_count < len(backoffs)
            ):
                await self._sleep(backoffs[retry_count])
                retry_count += 1
                continue

            self._raise_for_status(response, path)
            if response.status_code == 204 or not response.content:
                return {"status": "success"}
            try:
                payload: Any = response.json()
            except ValueError as exc:
                raise ZentaoError(
                    ErrorCode.NETWORK_ERROR,
                    "ZenTao returned a non-JSON response.",
                ) from exc
            if not isinstance(payload, dict):
                raise ZentaoError(
                    ErrorCode.NETWORK_ERROR,
                    "ZenTao returned an unexpected JSON response.",
                )
            if payload.get("status") in {"failed", "error"}:
                raise ZentaoError(
                    ErrorCode.VALIDATION_ERROR,
                    "ZenTao rejected the request.",
                    details={"response": payload},
                )
            return payload

    @staticmethod
    def _raise_for_status(response: httpx.Response, path: str) -> None:
        status = response.status_code
        if status < 400:
            return
        if status == 403:
            raise ZentaoError(
                ErrorCode.PERMISSION_DENIED,
                "The ZenTao account does not have permission for this operation.",
            )
        if status == 404:
            code = ErrorCode.BUG_NOT_FOUND if "/bugs/" in path else ErrorCode.VALIDATION_ERROR
            raise ZentaoError(code, "The requested ZenTao object was not found.")
        if 400 <= status < 500:
            raise ZentaoError(
                ErrorCode.VALIDATION_ERROR,
                f"ZenTao rejected the request with HTTP {status}.",
            )
        raise ZentaoError(
            ErrorCode.NETWORK_ERROR,
            f"ZenTao returned HTTP {status}.",
            retryable=True,
        )
