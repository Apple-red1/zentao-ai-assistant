from __future__ import annotations

import pytest

from zentao_ai.actions import BugActionService
from zentao_ai.errors import ErrorCode, ZentaoError
from zentao_ai.models import Settings, WriteAuthorization, WriteSettings, ZentaoSettings


class Stub:
    pass


def service(*, writes_enabled: bool = True) -> BugActionService:
    settings = Settings(
        version=1,
        zentao=ZentaoSettings(base_url="https://z.example", account="me"),
        writes=WriteSettings(enabled=writes_enabled),
    )
    return BugActionService(Stub(), Stub(), Stub(), settings)  # type: ignore[arg-type]


def test_write_requires_current_turn_authorization() -> None:
    with pytest.raises(ZentaoError) as exc:
        service().validate_authorization(
            WriteAuthorization(confirm=False, bug_id=123, action="assign"),
            expected_action="assign",
            bug_id=123,
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


def test_disabled_writes_cannot_be_confirmed() -> None:
    with pytest.raises(ZentaoError) as exc:
        service(writes_enabled=False).validate_authorization(
            WriteAuthorization(confirm=True, bug_id=123, action="assign"),
            expected_action="assign",
            bug_id=123,
        )

    assert exc.value.code is ErrorCode.CAPABILITY_UNAVAILABLE


def test_authorization_must_match_action_and_bug() -> None:
    with pytest.raises(ZentaoError) as exc:
        service().validate_authorization(
            WriteAuthorization(confirm=True, bug_id=123, action="edit"),
            expected_action="assign",
            bug_id=124,
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


def test_delete_is_not_an_action() -> None:
    assert "delete_bug" not in dir(BugActionService)
    assert "remove_bug" not in dir(BugActionService)

