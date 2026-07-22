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
    StepUpdateResult,
)


CONFIG = AppConfig.model_validate(
    {
        "personal": {"scopeNames": ["mine"]},
        "team": {"scopeNames": ["team"], "members": ["alice"]},
        "permissions": {"commentEnabled": True, "stepUpdateEnabled": True},
        "repositories": {},
    }
)

ROUTING_CONFIG = AppConfig.model_validate(
    {
        "personal": {"scopeNames": ["ce-site-backend", "cms-center"]},
        "team": {"scopeNames": ["ce-site-backend"], "members": ["alice"]},
        "permissions": {"commentEnabled": True, "stepUpdateEnabled": True},
        "repositories": {
            "ce-site-backend": {
                "repository": "ce-site-backend",
                "path": "C:/repo/web",
                "targetBranch": "wwt_play",
                "testCommands": ["pytest -q"],
            },
            "cms-center": {
                "repository": "cms-center",
                "path": "C:/repo/api",
                "targetBranch": "main",
                "testCommands": ["pytest -q"],
            },
        },
        "titleRouting": [
            {
                "marker": "【站点后台】",
                "frontendRepository": "ce-site-backend",
                "backendRepository": "cms-center",
            }
        ],
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


def routing_runtime(provider: Provider | None = None) -> AppRuntime:
    return AppRuntime(
        ROUTING_CONFIG,
        provider or Provider(),
        Ledger(),
        lambda: datetime(2026, 7, 15),
        "mcp",
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


def test_detail_adds_deterministic_title_routing_when_upstream_has_none() -> None:
    class RoutingProvider(Provider):
        def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
            return BugSnapshot(
                id=bug_id,
                status="active",
                creator="weiwenting",
                assignee="weiwenting",
                version="v1",
                snapshotVersion="s1",
                title="【站点后台】登录按钮背景色改为白色，文字改为黑色",
                steps="[步骤]登录页按钮演示\n[结果]登录按钮黑底白字\n[期望]登录按钮背景色改为白色，文字改为黑色",
                routing=None,
            )

    result = ZentaoTools(routing_runtime(RoutingProvider())).call(
        "query_bug_detail", {"bugId": 3397}
    )
    assert result["data"]["routing"]["selectedRepository"] == "ce-site-backend"
    assert result["data"]["routing"]["layer"] == "frontend"


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
async def test_tool_errors_are_structured_and_redacted() -> None:
    class FailingProvider(Provider):
        def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
            raise RuntimeError("token=must-not-leak")

    result = await execute_tool(
        ZentaoTools(runtime(FailingProvider())), "query_bug_detail", {"bugId": 7}
    )
    assert result.isError is True
    assert result.structuredContent == {
        "version": "v1",
        "data": None,
        "error": {"type": "RuntimeError", "message": "tool operation failed"},
    }
    assert "must-not-leak" not in str(result)
