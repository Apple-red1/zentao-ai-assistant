from __future__ import annotations

from typing import Any

import pytest

from zentao_ai.errors import ErrorCode, ZentaoError
from zentao_ai.models import TeamMember
from zentao_ai.users import UserDirectory


class FakeClient:
    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        **kwargs: object,
    ) -> dict[str, Any]:
        return {
            "status": "success",
            "users": [
                {"id": 1, "account": "zhangsan", "realname": "张三"},
                {"id": 2, "account": "zhangsan2", "realname": "张三"},
                {"id": 3, "account": "LiSi", "realname": "李四"},
            ],
            "pager": {"pageTotal": 1},
        }


async def directory() -> UserDirectory:
    result = UserDirectory(FakeClient())
    await result.list_users(kind="inside")
    return result


async def test_resolve_prefers_exact_account() -> None:
    users = await directory()
    assert users.resolve_cached("zhangsan").account == "zhangsan"


async def test_duplicate_real_name_is_ambiguous() -> None:
    users = await directory()

    with pytest.raises(ZentaoError) as exc:
        users.resolve_cached("张三")

    assert exc.value.code is ErrorCode.USER_AMBIGUOUS
    assert {item["account"] for item in exc.value.details["candidates"]} == {
        "zhangsan",
        "zhangsan2",
    }


async def test_account_match_is_case_insensitive_after_exact_name_rules() -> None:
    users = await directory()
    assert users.resolve_cached("lisi").account == "LiSi"


async def test_missing_user_has_stable_error() -> None:
    users = await directory()

    with pytest.raises(ZentaoError) as exc:
        users.resolve_cached("nobody")

    assert exc.value.code is ErrorCode.USER_NOT_FOUND


async def test_team_validation_isolates_invalid_members() -> None:
    users = await directory()

    result = await users.validate_team(
        [
            TeamMember(name="李四", account="LiSi"),
            TeamMember(name="错误姓名", account="zhangsan"),
        ]
    )

    assert [item.account for item in result.resolved] == ["LiSi"]
    assert result.failures[0].account == "zhangsan"

