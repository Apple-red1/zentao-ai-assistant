from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest
import respx

from zentao_ai.client import ZentaoClient
from zentao_ai.errors import ErrorCode, ZentaoError
from zentao_ai.models import Settings, ZentaoSettings


@dataclass
class MemoryCredentialStore:
    password: str | None = "secret"
    token: str | None = "stale"

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


async def test_401_refreshes_once_and_replays_request() -> None:
    store = MemoryCredentialStore()
    async with respx.mock:
        users = respx.get("https://z.example/api.php/v2/users").mock(
            side_effect=[
                httpx.Response(401),
                httpx.Response(200, json={"status": "success", "users": []}),
            ]
        )
        login = respx.post("https://z.example/api.php/v2/users/login").mock(
            return_value=httpx.Response(
                200,
                json={"status": "success", "token": "fresh"},
            )
        )
        async with ZentaoClient(settings(), store) as client:
            result = await client.request_json("GET", "/users")

    assert result == {"status": "success", "users": []}
    assert users.call_count == 2
    assert login.call_count == 1
    assert store.token == "fresh"


async def test_write_timeout_is_unknown_and_not_retried() -> None:
    store = MemoryCredentialStore(token="token")
    async with respx.mock:
        route = respx.put("https://z.example/api.php/v2/bugs/1").mock(
            side_effect=httpx.ReadTimeout("late")
        )
        async with ZentaoClient(settings(), store) as client:
            with pytest.raises(ZentaoError) as exc:
                await client.request_json(
                    "PUT",
                    "/bugs/1",
                    json={"title": "x"},
                    write=True,
                )

    assert exc.value.code is ErrorCode.UNKNOWN_WRITE_RESULT
    assert route.call_count == 1


async def test_permission_error_has_stable_code() -> None:
    store = MemoryCredentialStore(token="token")
    async with respx.mock:
        respx.get("https://z.example/api.php/v2/bugs/1").mock(
            return_value=httpx.Response(403, json={"message": "forbidden"})
        )
        async with ZentaoClient(settings(), store) as client:
            with pytest.raises(ZentaoError) as exc:
                await client.request_json("GET", "/bugs/1")

    assert exc.value.code is ErrorCode.PERMISSION_DENIED


async def test_external_url_is_rejected_before_request() -> None:
    store = MemoryCredentialStore(token="token")
    async with ZentaoClient(settings(), store) as client:
        with pytest.raises(ZentaoError) as exc:
            await client.request_json("GET", "https://attacker.example/bugs")

    assert exc.value.code is ErrorCode.VALIDATION_ERROR
