from __future__ import annotations

import asyncio
from typing import Any

import httpx

from zentao_ai.credentials import CredentialStore, normalize_base_url
from zentao_ai.errors import ErrorCode, ZentaoError
from zentao_ai.models import Settings


class AuthManager:
    def __init__(
        self,
        settings: Settings,
        credentials: CredentialStore,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._settings = settings
        self._credentials = credentials
        self._http = http_client
        self._base_url = normalize_base_url(str(settings.zentao.base_url))
        self._account = settings.zentao.account
        self._token: str | None = None
        self._lock = asyncio.Lock()

    async def get_token(self, force_refresh: bool = False) -> str:
        if not force_refresh:
            token = self._token or self._credentials.get_token(self._base_url, self._account)
            if token:
                self._token = token
                return token

        async with self._lock:
            if force_refresh:
                self._credentials.delete_token(self._base_url, self._account)
                self._token = None
            else:
                token = self._token or self._credentials.get_token(
                    self._base_url,
                    self._account,
                )
                if token:
                    self._token = token
                    return token
            return await self._login()

    async def refresh_after_unauthorized(self, failed_token: str) -> str:
        async with self._lock:
            current = self._token or self._credentials.get_token(
                self._base_url,
                self._account,
            )
            if current and current != failed_token:
                self._token = current
                return current
            self._credentials.delete_token(self._base_url, self._account)
            self._token = None
            return await self._login()

    async def _login(self) -> str:
        password = self._credentials.get_password(self._base_url, self._account)
        if not password:
            raise ZentaoError(
                ErrorCode.AUTH_ERROR,
                "No local ZenTao password is available; run `zentao-ai setup`.",
            )

        try:
            response = await self._http.post(
                f"{self._base_url}/api.php/v2/users/login",
                json={"account": self._account, "password": password},
            )
        except httpx.HTTPError as exc:
            raise ZentaoError(
                ErrorCode.NETWORK_ERROR,
                "Unable to reach ZenTao while signing in.",
                retryable=True,
            ) from exc

        if response.status_code in {401, 403}:
            raise ZentaoError(
                ErrorCode.AUTH_ERROR,
                "ZenTao rejected the configured account or password.",
            )
        if response.status_code >= 400:
            raise ZentaoError(
                ErrorCode.AUTH_ERROR,
                f"ZenTao sign-in failed with HTTP {response.status_code}.",
                retryable=response.status_code >= 500,
            )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise ZentaoError(
                ErrorCode.AUTH_ERROR,
                "ZenTao sign-in returned an invalid response.",
            ) from exc
        if not isinstance(payload, dict):
            raise ZentaoError(
                ErrorCode.AUTH_ERROR,
                "ZenTao sign-in returned an invalid response.",
            )
        token = payload.get("token")
        if not token and isinstance(payload.get("data"), dict):
            token = payload["data"].get("token")
        status = payload.get("status")
        if status not in {None, "success"} or not isinstance(token, str) or not token:
            raise ZentaoError(
                ErrorCode.AUTH_ERROR,
                "ZenTao sign-in did not return a usable token.",
            )

        self._credentials.set_token(self._base_url, self._account, token)
        self._token = token
        return token

