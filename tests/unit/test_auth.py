from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx
import respx

from zentao_ai.auth import AuthManager
from zentao_ai.models import Settings, ZentaoSettings


@dataclass
class MemoryCredentialStore:
    password: str | None = "secret"
    token: str | None = None

    def get_password(self, base_url: str, account: str) -> str | None:
        return self.password

    def set_password(self, base_url: str, account: str, password: str) -> None:
        self.password = password

    def get_token(self, base_url: str, account: str) -> str | None:
        return self.token

    def set_token(self, base_url: str, account: str, token: str) -> None:
        self.token = token

    def delete_token(self, base_url: str, account: str) -> None:
        self.token = None


def settings() -> Settings:
    return Settings(
        version=1,
        zentao=ZentaoSettings(base_url="https://z.example", account="me"),
    )


async def test_cached_token_avoids_login() -> None:
    store = MemoryCredentialStore(token="cached")
    async with httpx.AsyncClient() as http:
        manager = AuthManager(settings(), store, http)
        assert await manager.get_token() == "cached"


async def test_login_stores_fresh_token() -> None:
    store = MemoryCredentialStore()
    async with respx.mock:
        route = respx.post("https://z.example/api.php/v2/users/login").mock(
            return_value=httpx.Response(
                200,
                json={"status": "success", "token": "fresh"},
            )
        )
        async with httpx.AsyncClient() as http:
            manager = AuthManager(settings(), store, http)
            assert await manager.get_token() == "fresh"

    assert route.call_count == 1
    assert store.token == "fresh"


async def test_concurrent_401_refresh_logs_in_once() -> None:
    store = MemoryCredentialStore(token="stale")
    async with respx.mock:
        route = respx.post("https://z.example/api.php/v2/users/login").mock(
            return_value=httpx.Response(
                200,
                json={"status": "success", "token": "fresh"},
            )
        )
        async with httpx.AsyncClient() as http:
            manager = AuthManager(settings(), store, http)
            results = await asyncio.gather(
                manager.refresh_after_unauthorized("stale"),
                manager.refresh_after_unauthorized("stale"),
            )

    assert results == ["fresh", "fresh"]
    assert route.call_count == 1

