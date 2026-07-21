from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from zentao_ai.cli.runtime import AppRuntime
from zentao_ai.config.models import AppConfig
from zentao_ai.mcp_server.schemas import (
    AddCommentInput,
    QueryBugDetailInput,
    QueryMyBugsInput,
    QueryUserBugsInput,
    UpdateStepsInput,
)
from zentao_ai.mcp_server.server import execute_tool
from zentao_ai.mcp_server.tools import TOOL_NAMES, ZentaoTools
from zentao_ai.state.models import OutboxRecord, OutboxStatus
from zentao_ai.zentao.models import (
    BugPage,
    BugSnapshot,
    BugStatistics,
    CommentWriteResult,
    Coverage,
    HistoryPage,
    ItemFailure,
    ResolvedIdentity,
    StepUpdateResult,
)
from zentao_ai.zentao.errors import (
    AmbiguousIdentityError,
    ContractError,
    IdentityNotFoundError,
    PermissionDeniedError,
)


CONFIG = AppConfig.model_validate(
    {
        "zentao": {"account": "weiwenting"},
        "personal": {"scopeNames": ["mine"]},
        "team": {"scopeNames": ["team"], "members": ["alice"]},
        "permissions": {"commentEnabled": True, "stepUpdateEnabled": True},
        "repositories": {},
    }
)


class Provider:
    def __init__(self, comment_status: str = "CREATED") -> None:
        self.calls: list[tuple[object, ...]] = []
        self.comment_status = comment_status

    def query_my_bugs(self, **kwargs: object) -> BugPage:
        self.calls.append(("mine", kwargs))
        return BugPage(items=(self.query_bug_detail(7),), coverage=Coverage(total=1))

    def query_user_bugs(self, user: str, **kwargs: object) -> BugPage:
        self.calls.append(("user", user, kwargs))
        return BugPage(items=(), coverage=Coverage(total=0))

    def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
        self.calls.append(("detail", bug_id))
        return BugSnapshot(
            id=bug_id,
            status="active",
            creator="alice",
            version="v7",
            snapshotVersion="s7",
        )

    def query_bug_history(self, bug_id: int | str, **kwargs: object) -> HistoryPage:
        self.calls.append(("history", bug_id, kwargs))
        return HistoryPage(items=(), coverage=Coverage(total=0))

    def bug_statistics(self) -> BugStatistics:
        return BugStatistics(values={"active": 2})

    def add_bug_comment(
        self, bug_id: int | str, comment: str, confirm: bool, key: str
    ) -> CommentWriteResult:
        self.calls.append(("comment", bug_id, comment, confirm, key))
        return CommentWriteResult(
            created=self.comment_status == "CREATED",
            alreadyExists=self.comment_status == "ALREADY_EXISTS",
            commentId=None if self.comment_status == "UNKNOWN" else "c1",
            status=self.comment_status,
        )

    def reconcile_comment(
        self, key: str, bug_id: int | str, **kwargs: object
    ) -> CommentWriteResult:
        return CommentWriteResult(
            created=False, alreadyExists=False, commentId=None, status="UNKNOWN"
        )

    def update_bug_steps(
        self, bug_id: int | str, steps: str, confirm: bool = True
    ) -> StepUpdateResult:
        self.calls.append(("steps", bug_id, steps, confirm))
        return StepUpdateResult(updated=True, bugId=bug_id, version="v8")

    def update_bug_steps_with_image(
        self,
        bug_id: int | str,
        steps: str,
        image: bytes,
        filename: str,
        content_type: str,
        confirm: bool = True,
    ) -> StepUpdateResult:
        self.calls.append(
            ("image", bug_id, steps, image, filename, content_type, confirm)
        )
        return StepUpdateResult(updated=True, bugId=bug_id, version="v8")


class AssigneeProvider(Provider):
    def query_my_bugs(self, **kwargs: object) -> BugPage:
        raise AssertionError("personal endpoint must not be used")

    def query_user_bugs(self, user: str, **kwargs: object) -> BugPage:
        self.calls.append(("user", user, kwargs))
        return BugPage(
            items=(
                BugSnapshot(
                    id=2537,
                    title="【AI建站】 first",
                    status="active",
                    version="v1",
                    snapshotVersion="s1",
                ),
                BugSnapshot(
                    id=3397,
                    title="【站点后台】 second",
                    status="open",
                    version="v1",
                    snapshotVersion="s2",
                ),
            ),
            coverage=Coverage(page=1, pageSize=20, total=2, pages=1),
        )


class Ledger:
    def put_outbox(self, record: OutboxRecord) -> OutboxRecord:
        return OutboxRecord(
            record.idempotency_key,
            record.run_kind,
            record.payload,
            status=OutboxStatus.PENDING,
        )

    def mark_outbox_result(
        self, key: str, status: OutboxStatus, external_id: str | None
    ) -> OutboxRecord:
        return OutboxRecord(key, "comment", {}, status=status, external_id=external_id)

    def reconcile_outbox(
        self, key: str, status: OutboxStatus, external_id: str | None
    ) -> OutboxRecord:
        return self.mark_outbox_result(key, status, external_id)


def runtime(provider: Provider | None = None) -> AppRuntime:
    return AppRuntime(
        CONFIG, provider or Provider(), Ledger(), lambda: datetime(2026, 7, 15), "mcp"
    )


def authorization(
    action: str,
    parameters: dict[str, object],
    *,
    bug_id: int | str = 7,
    paths: tuple[Path, ...] = (),
    turn_id: str = "turn-1",
    source: str = "user",
) -> dict[str, object]:
    return {
        "currentTurnId": "turn-1",
        "authorization": {
            "turnId": turn_id,
            "source": source,
            "action": action,
            "bugId": bug_id,
            "parameters": parameters,
            "authorizedImagePaths": [str(path) for path in paths],
        },
    }


def test_tool_list_is_exact_and_has_no_destructive_equivalent() -> None:
    assert TOOL_NAMES == (
        "query_my_bugs",
        "query_user_bugs",
        "query_bug_detail",
        "query_bug_history",
        "bug_statistics",
        "add_bug_comment",
        "update_bug_steps",
        "update_bug_steps_with_image",
    )
    assert not (
        {"delete", "remove", "assign", "resolve", "close", "activate", "convert"}
        & set("_".join(TOOL_NAMES).split("_"))
    )


def test_schemas_reject_unknown_and_invalid_write_arguments() -> None:
    query_user = QueryUserBugsInput.model_validate({"user": "alice"})
    assert query_user.scopeMode == "team-report"
    assert query_user.status == "all"
    with pytest.raises(ValidationError):
        QueryBugDetailInput.model_validate({"bugId": 7, "extra": True})
    with pytest.raises(ValidationError):
        AddCommentInput.model_validate(
            {"bugId": 7, "comment": " ", "confirm": True, "idempotencyKey": "k"}
        )
    with pytest.raises(ValidationError):
        AddCommentInput.model_validate(
            {"bugId": 7, "comment": "x", "confirm": False, "idempotencyKey": "k"}
        )
    with pytest.raises(ValidationError):
        QueryBugDetailInput.model_validate({"bugId": True})
    with pytest.raises(ValidationError):
        QueryMyBugsInput.model_validate({"page": "1"})
    with pytest.raises(ValidationError):
        UpdateStepsInput.model_validate(
            {
                "bugId": 7,
                "steps": [{"action": "open page", "expected": "page loads"}],
                "confirm": True,
                "currentTurnId": "turn-1",
                "authorization": {
                    "turnId": "turn-1",
                    "source": "user",
                    "action": "update_steps",
                    "bugId": 7,
                    "parameters": {"steps": []},
                    "unknown": True,
                },
            }
        )


def test_all_read_tools_return_stable_versioned_structured_content() -> None:
    tools = ZentaoTools(runtime())
    calls = {
        "query_my_bugs": {},
        "query_user_bugs": {"user": "alice"},
        "query_bug_detail": {"bugId": 7},
        "query_bug_history": {"bugId": 7},
        "bug_statistics": {},
    }
    for name, arguments in calls.items():
        result = tools.call(name, arguments)
        assert result["version"] == "v1"
        assert "data" in result and "snapshotVersion" not in result
    assert (
        tools.call("query_bug_detail", {"bugId": 7})["data"]["snapshotVersion"] == "s7"
    )


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ({"titleTag": "AI建站", "status": "all"}, [2537]),
        ({"titleTag": "站点后台", "status": "unclosed"}, [3397]),
        ({"status": "unclosed"}, [2537, 3397]),
    ],
)
def test_query_my_bugs_routes_through_configured_assignee_and_filters(
    arguments: dict[str, object], expected: list[int]
) -> None:
    provider = AssigneeProvider()
    result = ZentaoTools(runtime(provider)).call("query_my_bugs", arguments)
    assert [item["id"] for item in result["data"]["items"]] == expected
    assert provider.calls == [
        (
            "user",
            "weiwenting",
            {
                "scope_names": (),
                "page": 1,
                "page_size": 20,
                "browse_type": "assigntome",
            },
        )
    ]


def test_personal_tool_sets_assignee_filter_but_arbitrary_user_tool_does_not() -> None:
    provider = AssigneeProvider()

    ZentaoTools(runtime(provider)).call("query_my_bugs", {})
    ZentaoTools(runtime(provider)).call("query_user_bugs", {"user": "alice"})

    assert provider.calls == [
        (
            "user",
            "weiwenting",
            {
                "scope_names": (),
                "page": 1,
                "page_size": 20,
                "browse_type": "assigntome",
            },
        ),
        (
            "user",
            "alice",
            {"scope_names": ("team",), "page": 1, "page_size": 20},
        ),
    ]


def test_query_user_bugs_defaults_to_team_report_and_requires_a_configured_member() -> (
    None
):
    provider = AssigneeProvider()
    tools = ZentaoTools(runtime(provider))

    tools.call("query_user_bugs", {"user": "alice"})

    with pytest.raises(ValueError, match="configured team member"):
        tools.call("query_user_bugs", {"user": "周海韵"})

    assert provider.calls == [
        (
            "user",
            "alice",
            {"scope_names": ("team",), "page": 1, "page_size": 20},
        )
    ]


def test_query_user_bugs_session_visible_uses_explicit_user_without_team_scope() -> (
    None
):
    provider = AssigneeProvider()
    config_before = runtime(provider).config.model_dump()
    tools = ZentaoTools(runtime(provider))

    result = tools.call(
        "query_user_bugs",
        {"user": "周海韵", "scopeMode": "session-visible", "status": "unclosed"},
    )

    assert [item["id"] for item in result["data"]["items"]] == [2537, 3397]
    assert provider.calls == [
        (
            "user",
            "周海韵",
            {"scope_names": (), "page": 1, "page_size": 20},
        )
    ]
    assert tools.runtime.config.model_dump() == config_before


def test_query_user_bugs_keeps_partial_metadata_after_status_filtering() -> None:
    provider = AssigneeProvider()
    provider.query_user_bugs = lambda user, **kwargs: BugPage(  # type: ignore[method-assign]
        items=(
            BugSnapshot(
                id=2537,
                title="visible",
                status="active",
                version="v1",
                snapshotVersion="s1",
            ),
            BugSnapshot(
                id=3397,
                title="closed",
                status="closed",
                version="v1",
                snapshotVersion="s2",
            ),
        ),
        coverage=Coverage(
            page=1,
            pageSize=20,
            total=-1,
            pages=None,
            returned=2,
            failed=1,
            complete=False,
        ),
        itemFailures=(
            ItemFailure(
                bugId="3398",
                code="MISSING_STABLE_VERSION",
                field="version",
                message="missing stable version",
            ),
        ),
        resolvedIdentity=ResolvedIdentity(
            requestedIdentity="周海韵",
            resolvedAccount="zhouhaiyun",
            resolvedDisplayName="周海韵",
            matchType="display_name",
        ),
    )

    data = ZentaoTools(runtime(provider)).call(
        "query_user_bugs",
        {"user": "周海韵", "scopeMode": "session-visible", "status": "unclosed"},
    )["data"]

    assert [item["id"] for item in data["items"]] == [2537]
    assert data["coverage"] == {
        "page": 1,
        "pageSize": 20,
        "total": -1,
        "pages": None,
        "returned": 1,
        "failed": 1,
        "complete": False,
    }
    assert data["itemFailures"][0]["bugId"] == "3398"
    assert data["resolvedIdentity"]["resolvedAccount"] == "zhouhaiyun"


@pytest.mark.parametrize("account", [None, "", "   "])
def test_query_my_bugs_fails_closed_without_configured_account(
    account: str | None,
) -> None:
    config = CONFIG.model_copy(
        update={"zentao": CONFIG.zentao.model_copy(update={"account": account})}
    )
    provider = AssigneeProvider()
    with pytest.raises(RuntimeError, match="configuration"):
        ZentaoTools(
            AppRuntime(config, provider, Ledger(), lambda: datetime(2026, 7, 15), "mcp")
        ).call("query_my_bugs", {})
    assert provider.calls == []


def test_query_my_bugs_keeps_filtered_candidates_with_unknown_incomplete_coverage() -> (
    None
):
    provider = AssigneeProvider()
    provider.query_user_bugs = lambda user, **kwargs: BugPage(  # type: ignore[method-assign]
        items=(
            BugSnapshot(
                id=2537,
                title="【AI建站】 first",
                status="active",
                version="v1",
                snapshotVersion="s1",
            ),
            BugSnapshot(
                id=3397,
                title="【站点后台】 second",
                status="open",
                version="v1",
                snapshotVersion="s2",
            ),
        ),
        coverage=Coverage(page=1, pageSize=20, total=99, pages=None),
    )
    data = ZentaoTools(runtime(provider)).call("query_my_bugs", {"titleTag": "AI建站"})[
        "data"
    ]
    assert [item["id"] for item in data["items"]] == [2537]
    assert data["coverage"] == {
        "page": 1,
        "pageSize": 20,
        "total": -1,
        "pages": None,
        "returned": 1,
        "failed": 0,
        "complete": False,
    }


def test_query_my_bugs_preserves_partial_result_metadata() -> None:
    provider = AssigneeProvider()
    provider.query_user_bugs = lambda user, **kwargs: BugPage(  # type: ignore[method-assign]
        items=(
            BugSnapshot(
                id=2537,
                title="AI candidate",
                status="active",
                version="v1",
                snapshotVersion="s1",
            ),
        ),
        coverage=Coverage(
            page=1,
            pageSize=20,
            total=-1,
            pages=None,
            returned=1,
            failed=1,
            complete=False,
        ),
        itemFailures=(
            ItemFailure(
                bugId="3397",
                code="MISSING_STABLE_VERSION",
                field="version",
                message="missing stable version",
            ),
        ),
        resolvedIdentity=ResolvedIdentity(
            requestedIdentity="weiwenting",
            resolvedAccount="wwt",
            resolvedDisplayName="Wei Wen Ting",
            matchType="display_name",
        ),
    )

    data = ZentaoTools(runtime(provider)).call("query_my_bugs", {})["data"]

    assert data["coverage"] == {
        "page": 1,
        "pageSize": 20,
        "total": -1,
        "pages": None,
        "returned": 1,
        "failed": 1,
        "complete": False,
    }
    assert data["itemFailures"] == [
        {
            "bugId": "3397",
            "code": "MISSING_STABLE_VERSION",
            "field": "version",
            "message": "missing stable version",
        }
    ]
    assert data["resolvedIdentity"]["resolvedAccount"] == "wwt"


def test_query_my_bugs_distrusts_multi_page_total_when_visible_items_all_pass() -> None:
    provider = AssigneeProvider()
    provider.query_user_bugs = lambda user, **kwargs: BugPage(  # type: ignore[method-assign]
        items=(
            BugSnapshot(
                id=2537,
                title="【AI建站】 first",
                status="active",
                version="v1",
                snapshotVersion="s1",
            ),
            BugSnapshot(
                id=3397,
                title="【站点后台】 second",
                status="open",
                version="v1",
                snapshotVersion="s2",
            ),
        ),
        coverage=Coverage(page=1, pageSize=2, total=4, pages=2),
    )
    data = ZentaoTools(runtime(provider)).call(
        "query_my_bugs", {"status": "unclosed", "pageSize": 2}
    )["data"]
    assert [item["id"] for item in data["items"]] == [2537, 3397]
    assert data["coverage"] == {
        "page": 1,
        "pageSize": 2,
        "total": -1,
        "pages": None,
        "returned": 2,
        "failed": 0,
        "complete": False,
    }


def test_query_my_bugs_distrusts_zero_pages_with_nonempty_items() -> None:
    provider = AssigneeProvider()
    provider.query_user_bugs = lambda user, **kwargs: BugPage(  # type: ignore[method-assign]
        items=(
            BugSnapshot(
                id=2537,
                title="【AI建站】 first",
                status="active",
                version="v1",
                snapshotVersion="s1",
            ),
        ),
        coverage=Coverage(page=1, pageSize=20, total=1, pages=0),
    )
    data = ZentaoTools(runtime(provider)).call("query_my_bugs", {})["data"]
    assert [item["id"] for item in data["items"]] == [2537]
    assert data["coverage"] == {
        "page": 1,
        "pageSize": 20,
        "total": -1,
        "pages": None,
        "returned": 1,
        "failed": 0,
        "complete": False,
    }


@pytest.mark.parametrize("status", ["CREATED", "ALREADY_EXISTS", "UNKNOWN"])
def test_comment_uses_shared_gated_writer_and_preserves_trimmed_key(
    status: str,
) -> None:
    provider = Provider(status)
    tools = ZentaoTools(runtime(provider))
    auth = authorization("comment", {"comment": "hello"})
    result = tools.call(
        "add_bug_comment",
        {
            "bugId": 7,
            "comment": "  hello  ",
            "confirm": True,
            "idempotencyKey": "  request-key  ",
            **auth,
            "snapshotStable": True,
            "historyChecked": True,
            "cooldownPassed": True,
            "idempotencyPassed": True,
        },
    )
    assert result["data"]["status"] == status
    assert result["data"]["idempotencyKey"] == "request-key"
    assert ("comment", 7, "hello", True, "request-key") in provider.calls


@pytest.mark.parametrize(
    "field", ["snapshotStable", "historyChecked", "cooldownPassed", "idempotencyPassed"]
)
def test_comment_rejects_each_missing_gate(field: str) -> None:
    args = {
        "bugId": 7,
        "comment": "hello",
        "confirm": True,
        "idempotencyKey": "request-key",
        **authorization("comment", {"comment": "hello"}),
        "snapshotStable": True,
        "historyChecked": True,
        "cooldownPassed": True,
        "idempotencyPassed": True,
    }
    args[field] = False
    result = ZentaoTools(runtime()).call("add_bug_comment", args)
    assert result["data"]["status"] == "SKIPPED"


def test_steps_require_exact_current_turn_authorization() -> None:
    provider = Provider()
    tools = ZentaoTools(runtime(provider))
    params = {"steps": [{"action": "open page", "expected": "page loads"}]}
    args = {
        "bugId": 7,
        "steps": [{"action": "open page", "expected": "page loads"}],
        "confirm": True,
        "scheduled": False,
        **authorization("update_steps", params),
    }
    assert tools.call("update_bug_steps", args)["data"]["updated"] is True
    args["scheduled"] = True
    with pytest.raises(PermissionError):
        tools.call("update_bug_steps", args)


@pytest.mark.parametrize(
    ("change", "value"),
    [
        ("turnId", "old"),
        ("source", "bug"),
        ("action", "update_steps_with_image"),
        ("bugId", 8),
        ("parameters", {"steps": []}),
    ],
)
def test_plain_steps_reject_every_inexact_independent_authorization(
    change: str,
    value: object,
) -> None:
    params = {"steps": [{"action": "open page", "expected": "page loads"}]}
    args = {
        "bugId": 7,
        "steps": params["steps"],
        "confirm": True,
        **authorization("update_steps", params),
    }
    args["authorization"][change] = value  # type: ignore[index]
    with pytest.raises((PermissionError, ValidationError)):
        ZentaoTools(runtime()).call("update_bug_steps", args)


def test_image_uses_only_independently_authorized_absolute_path_and_magic(
    tmp_path: Path,
) -> None:
    image = (tmp_path / "proof.png").resolve()
    image.write_bytes(b"\x89PNG\r\n\x1a\nproof")
    params = {
        "steps": [{"action": "open page", "expected": "page loads"}],
        "imagePath": str(image),
        "filename": "proof.png",
    }
    args = {
        "bugId": 7,
        "steps": params["steps"],
        "imagePath": str(image),
        "confirm": True,
        **authorization("update_steps_with_image", params, paths=(image,)),
    }
    provider = Provider()
    assert ZentaoTools(runtime(provider)).call("update_bug_steps_with_image", args)[
        "data"
    ]["updated"]
    assert provider.calls[-1][0] == "image"

    other = (tmp_path / "other.png").resolve()
    other.write_bytes(b"\x89PNG\r\n\x1a\nother")
    args["imagePath"] = str(other)
    with pytest.raises(PermissionError):
        ZentaoTools(runtime()).call("update_bug_steps_with_image", args)

    image.write_bytes(b"not-png")
    args["imagePath"] = str(image)
    with pytest.raises(PermissionError, match="IMAGE_MAGIC_MISMATCH"):
        ZentaoTools(runtime()).call("update_bug_steps_with_image", args)


def test_relative_authorized_image_path_is_rejected_without_provider_write(
    tmp_path: Path,
) -> None:
    image = (tmp_path / "proof.png").resolve()
    image.write_bytes(b"\x89PNG\r\n\x1a\nproof")
    params = {
        "steps": [{"action": "open page", "expected": "page loads"}],
        "imagePath": str(image),
        "filename": image.name,
    }
    args = {
        "bugId": 7,
        "steps": params["steps"],
        "imagePath": str(image),
        "confirm": True,
        **authorization("update_steps_with_image", params, paths=(image,)),
    }
    args["authorization"]["authorizedImagePaths"] = ["proof.png"]  # type: ignore[index]
    provider = Provider()
    with pytest.raises(ValidationError):
        ZentaoTools(runtime(provider)).call("update_bug_steps_with_image", args)
    assert not any(call[0] == "image" for call in provider.calls)


@pytest.mark.parametrize("bad", ["", "   ", "bad\x00path.png"])
def test_blank_or_nul_authorized_image_path_is_rejected(bad: str) -> None:
    with pytest.raises(ValidationError):
        AddCommentInput.model_validate(
            {
                "bugId": 7,
                "comment": "hello",
                "confirm": True,
                "idempotencyKey": "key",
                "currentTurnId": "turn",
                "authorization": {
                    "turnId": "turn",
                    "source": "user",
                    "action": "comment",
                    "bugId": 7,
                    "parameters": {"comment": "hello"},
                    "authorizedImagePaths": [bad],
                },
                "snapshotStable": True,
                "historyChecked": True,
                "cooldownPassed": True,
                "idempotencyPassed": True,
            }
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected_error"),
    [
        (
            IdentityNotFoundError("session=secret-marker"),
            {
                "code": "IDENTITY_NOT_FOUND",
                "type": "identity_not_found",
                "message": "Requested identity was not found.",
            },
        ),
        (
            AmbiguousIdentityError("cookie=secret-marker"),
            {
                "code": "AMBIGUOUS_IDENTITY",
                "type": "ambiguous_identity",
                "message": "Requested identity is ambiguous.",
            },
        ),
        (
            PermissionDeniedError("authorization=secret-marker"),
            {
                "code": "PERMISSION_DENIED",
                "type": "permission_denied",
                "message": "Permission was denied.",
            },
        ),
        (
            ContractError("response_body=secret-marker"),
            {
                "code": "INVALID_ENVELOPE",
                "type": "invalid_envelope",
                "message": "Received an invalid Zentao response.",
            },
        ),
        (
            RuntimeError("token=secret-marker"),
            {
                "code": "INTERNAL_ERROR",
                "type": "internal_error",
                "message": "An internal error occurred.",
            },
        ),
    ],
)
async def test_tool_errors_are_structured_sanitized_and_stable(
    error: Exception, expected_error: dict[str, str]
) -> None:
    class FailingProvider(Provider):
        def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
            raise error

    result = await execute_tool(
        ZentaoTools(runtime(FailingProvider())), "query_bug_detail", {"bugId": 7}
    )
    assert result.isError is True
    assert result.structuredContent == {
        "version": "v1",
        "data": None,
        "error": expected_error,
    }
    assert result.content[0].text == expected_error["message"]
    assert "secret-marker" not in str(result)
