from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from zentao_ai.cli.runtime import AppRuntime
from zentao_ai.config.models import AppConfig
from zentao_ai.mcp_server.schemas import AddCommentInput, QueryBugDetailInput
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


class Provider:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def query_my_bugs(self, **kwargs: object) -> BugPage:
        self.calls.append(("mine", kwargs))
        return BugPage(items=(self.query_bug_detail(7),), coverage=Coverage(total=1))

    def query_user_bugs(self, user: str, **kwargs: object) -> BugPage:
        self.calls.append(("user", user, kwargs))
        return BugPage(items=(), coverage=Coverage(total=0))

    def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
        self.calls.append(("detail", bug_id))
        return BugSnapshot(
            id=bug_id, status="active", creator="alice", version="v7", snapshotVersion="s7"
        )

    def query_bug_history(self, bug_id: int | str, **kwargs: object) -> HistoryPage:
        self.calls.append(("history", bug_id, kwargs))
        return HistoryPage(items=(), coverage=Coverage(total=0))

    def bug_statistics(self) -> BugStatistics:
        return BugStatistics(values={"active": 2})

    def add_bug_comment(self, bug_id: int | str, comment: str, confirm: bool, key: str) -> CommentWriteResult:
        self.calls.append(("comment", bug_id, comment, confirm, key))
        return CommentWriteResult(created=True, alreadyExists=False, commentId="c1", status="CREATED")

    def reconcile_comment(self, key: str, bug_id: int | str, **kwargs: object) -> CommentWriteResult:
        return CommentWriteResult(created=False, alreadyExists=False, commentId=None, status="UNKNOWN")

    def update_bug_steps(self, bug_id: int | str, steps: str, confirm: bool = True) -> StepUpdateResult:
        self.calls.append(("steps", bug_id, steps, confirm))
        return StepUpdateResult(updated=True, bugId=bug_id, version="v8")


class Ledger:
    def put_outbox(self, record: OutboxRecord) -> OutboxRecord:
        return OutboxRecord(record.idempotency_key, record.run_kind, record.payload, status=OutboxStatus.PENDING)

    def mark_outbox_result(self, key: str, status: OutboxStatus, external_id: str | None) -> OutboxRecord:
        return OutboxRecord(key, "comment", {}, status=status, external_id=external_id)

    def reconcile_outbox(self, key: str, status: OutboxStatus, external_id: str | None) -> OutboxRecord:
        return self.mark_outbox_result(key, status, external_id)


def runtime(provider: Provider | None = None) -> AppRuntime:
    return AppRuntime(CONFIG, provider or Provider(), Ledger(), lambda: datetime(2026, 7, 15), "mcp")


def test_tool_list_is_exact_and_has_no_destructive_equivalent() -> None:
    assert TOOL_NAMES == (
        "query_my_bugs", "query_user_bugs", "query_bug_detail",
        "query_bug_history", "bug_statistics", "add_bug_comment",
        "update_bug_steps", "update_bug_steps_with_image",
    )
    assert not ({"delete", "remove", "assign", "resolve", "close", "activate", "convert"} & set("_".join(TOOL_NAMES).split("_")))


def test_schemas_reject_unknown_and_invalid_write_arguments() -> None:
    with pytest.raises(ValidationError):
        QueryBugDetailInput.model_validate({"bugId": 7, "extra": True})
    with pytest.raises(ValidationError):
        AddCommentInput.model_validate({"bugId": 7, "comment": " ", "confirm": True, "idempotencyKey": "k"})
    with pytest.raises(ValidationError):
        AddCommentInput.model_validate({"bugId": 7, "comment": "x", "confirm": False, "idempotencyKey": "k"})


def test_all_read_tools_return_stable_versioned_structured_content() -> None:
    tools = ZentaoTools(runtime())
    calls = {
        "query_my_bugs": {}, "query_user_bugs": {"user": "alice"},
        "query_bug_detail": {"bugId": 7}, "query_bug_history": {"bugId": 7},
        "bug_statistics": {},
    }
    for name, arguments in calls.items():
        result = tools.call(name, arguments)
        assert result["version"] == "v1"
        assert "data" in result and "snapshotVersion" not in result
    assert tools.call("query_bug_detail", {"bugId": 7})["data"]["snapshotVersion"] == "s7"


def test_comment_uses_shared_gated_writer_and_preserves_trimmed_key() -> None:
    provider = Provider()
    tools = ZentaoTools(runtime(provider))
    result = tools.call(
        "add_bug_comment",
        {
            "bugId": 7, "comment": "  hello  ", "confirm": True,
            "idempotencyKey": "  request-key  ", "turnId": "turn-1",
            "authorizationRecords": [{"turnId": "turn-1", "source": "user", "action": "comment", "bugId": "7", "parameters": {"comment": "hello"}}],
            "snapshotStable": True, "historyChecked": True,
            "cooldownPassed": True, "idempotencyPassed": True,
        },
    )
    assert result["data"]["status"] == "CREATED"
    assert result["data"]["idempotencyKey"] == "request-key"
    assert ("comment", 7, "hello", True, "request-key") in provider.calls


def test_steps_require_exact_current_turn_authorization() -> None:
    provider = Provider()
    tools = ZentaoTools(runtime(provider))
    args = {
        "bugId": 7, "steps": [{"action": "open page", "expected": "page loads"}],
        "confirm": True, "turnId": "turn-1", "scheduled": False,
        "authorizationRecords": [{"turnId": "turn-1", "source": "user", "action": "update_steps", "bugId": "7", "parameters": {"steps": [{"action": "open page", "expected": "page loads"}]}}],
    }
    assert tools.call("update_bug_steps", args)["data"]["updated"] is True
    args["scheduled"] = True
    with pytest.raises(PermissionError):
        tools.call("update_bug_steps", args)


@pytest.mark.anyio
async def test_tool_errors_are_structured_and_redacted() -> None:
    class FailingProvider(Provider):
        def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
            raise RuntimeError("token=must-not-leak")

    result = await execute_tool(ZentaoTools(runtime(FailingProvider())), "query_bug_detail", {"bugId": 7})
    assert result.isError is True
    assert result.structuredContent == {
        "version": "v1", "data": None,
        "error": {"type": "RuntimeError", "message": "tool operation failed"},
    }
    assert "must-not-leak" not in str(result)
