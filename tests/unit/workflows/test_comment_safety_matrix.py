from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import pytest

from zentao_ai.config.models import AppConfig
from zentao_ai.safety.actions import AuthorizationRecord
from zentao_ai.state.models import OutboxRecord, OutboxStatus
from zentao_ai.workflows.comments import (
    write_information_comment,
    write_resolution_comment,
)
from zentao_ai.workflows.models import RunContext
from zentao_ai.zentao.models import BugSnapshot, CommentWriteResult


class RecordingLedger:
    def __init__(self, status: OutboxStatus = OutboxStatus.PENDING) -> None:
        self.status = status
        self.calls: list[tuple[object, ...]] = []

    def put_outbox(self, record: OutboxRecord) -> OutboxRecord:
        self.calls.append(("put", record))
        return replace(record, status=self.status)

    def mark_outbox_result(self, *args: object) -> OutboxRecord:
        self.calls.append(("mark", *args))
        return OutboxRecord(str(args[0]), "comment", {}, status=args[1])

    def reconcile_outbox(self, *args: object) -> OutboxRecord:
        self.calls.append(("reconcile", *args))
        return OutboxRecord(str(args[0]), "comment", {}, status=args[1])


class RecordingProvider:
    def __init__(self, *, timeout: bool = False, reconciled: str = "UNKNOWN") -> None:
        self.timeout = timeout
        self.reconciled = reconciled
        self.calls: list[tuple[object, ...]] = []

    def add_bug_comment(self, *args: object) -> CommentWriteResult:
        self.calls.append(("write", *args))
        if self.timeout:
            raise TimeoutError
        return CommentWriteResult(
            created=True, alreadyExists=False, commentId="c1", status="CREATED"
        )

    def reconcile_comment(self, *args: object, **kwargs: object) -> CommentWriteResult:
        self.calls.append(("reconcile", *args, kwargs))
        return CommentWriteResult(
            created=self.reconciled == "CREATED",
            alreadyExists=self.reconciled == "ALREADY_EXISTS",
            commentId="c1" if self.reconciled != "UNKNOWN" else None,
            status=self.reconciled,
        )


def snapshot() -> BugSnapshot:
    return BugSnapshot(
        id=7,
        status="active",
        version="v1",
        snapshotVersion="v1",
        creator={"account": "alice"},
    )


def context(
    provider: RecordingProvider,
    ledger: RecordingLedger,
    **changes: object,
) -> RunContext:
    config = AppConfig.model_validate(
        {
            "personal": {"scopeNames": ["mine"]},
            "team": {"scopeNames": ["team"], "members": ["alice"]},
            "permissions": {"commentEnabled": True},
            "repositories": {},
        }
    )
    base = RunContext(
        config,
        provider,  # type: ignore[arg-type]
        ledger,  # type: ignore[arg-type]
        lambda: datetime(2026, 7, 15, 9),
        "owner",
        currentTurnId="turn",
        snapshotStable=True,
        historyChecked=True,
        cooldownPassed=True,
        idempotencyPassed=True,
    )
    return replace(base, **changes)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("snapshotStable", False),
        ("historyChecked", False),
        ("cooldownPassed", False),
        ("idempotencyPassed", False),
        ("readonly", True),
        ("dryRun", True),
        ("scheduled", True),
    ],
)
def test_both_public_comment_writers_apply_every_gate(field: str, value: bool) -> None:
    for writer in (write_information_comment, write_resolution_comment):
        provider, ledger = RecordingProvider(), RecordingLedger()
        ctx = context(provider, ledger, **{field: value})
        body = "need logs" if writer is write_information_comment else "candidate"
        result = writer(ctx, snapshot(), body)
        assert result.status == "SKIPPED"
        assert provider.calls == [] and ledger.calls == []


def test_resolution_comment_timeout_immediately_reconciles_exact_payload() -> None:
    provider = RecordingProvider(timeout=True, reconciled="ALREADY_EXISTS")
    ledger = RecordingLedger()
    seed = context(provider, ledger)
    body = "candidate"
    from zentao_ai.workflows.comments import canonical_resolution_comment

    rendered = canonical_resolution_comment(body)
    authorized = replace(
        seed,
        authorizationRecords=(
            AuthorizationRecord(
                turnId="turn",
                source="user",
                action="comment",
                bugId="7",
                parameters={"comment": rendered},
            ),
        ),
    )
    result = write_resolution_comment(authorized, snapshot(), body)
    assert result.status == "ALREADY_EXISTS"
    assert provider.calls[1][0] == "reconcile"
    assert provider.calls[1][-1] == {"comment": rendered}
    assert [call[0] for call in ledger.calls] == ["put", "mark", "reconcile"]
