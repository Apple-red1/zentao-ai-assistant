from __future__ import annotations

from dataclasses import dataclass

import httpx
import respx

from zentao_ai.client import ZentaoClient
from zentao_ai.models import Settings, ZentaoSettings
from zentao_ai.users import UserDirectory


@dataclass
class MemoryCredentialStore:
    token: str | None = "token"

    def get_password(self, base_url: str, account: str) -> str | None:
        return "secret"

    def set_password(self, base_url: str, account: str, password: str) -> None:
        return None

    def get_token(self, base_url: str, account: str) -> str | None:
        return self.token

    def set_token(self, base_url: str, account: str, token: str) -> None:
        self.token = token

    def delete_token(self, base_url: str, account: str) -> None:
        self.token = None


async def test_outside_users_are_read_across_all_pages() -> None:
    settings = Settings(
        version=1,
        zentao=ZentaoSettings(base_url="https://z.example", account="me"),
    )
    async with respx.mock:
        route = respx.get("https://z.example/api.php/v2/users").mock(
            side_effect=[
                httpx.Response(
                    200,
                    json={
                        "users": [{"id": "5", "account": "external-a", "realname": "外部甲"}],
                        "pager": {"pageTotal": 2},
                    },
                ),
                httpx.Response(
                    200,
                    json={
                        "users": [{"id": "6", "account": "external-b", "realname": "外部乙"}],
                        "pager": {"pageTotal": 2},
                    },
                ),
            ]
        )
        async with ZentaoClient(settings, MemoryCredentialStore()) as client:
            directory = UserDirectory(client)
            user = await directory.resolve("external-a", kind="outside")
            all_users = await directory.list_users(kind="outside")

    assert user.kind == "outside"
    assert [item.account for item in all_users] == ["external-a", "external-b"]
    assert route.call_count == 2
    assert [call.request.url.params["page"] for call in route.calls] == ["1", "2"]
    assert all(call.request.url.params["browseType"] == "outside" for call in route.calls)
