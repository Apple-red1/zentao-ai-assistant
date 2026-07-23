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
from zentao_ai.workflows.snapshot_guard import unstable_snapshot_matches
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
    def __init__(
        self,
        *,
        timeout: bool = False,
        reconciled: str = "UNKNOWN",
        fresh_snapshot: BugSnapshot | None = None,
    ) -> None:
        self.timeout = timeout
        self.reconciled = reconciled
        self.fresh_snapshot = fresh_snapshot
        self.calls: list[tuple[object, ...]] = []

    def query_bug_detail(
        self, bug_id: int | str, *, allow_unstable: bool = False
    ) -> BugSnapshot:
        self.calls.append(("query", bug_id, allow_unstable))
        assert self.fresh_snapshot is not None
        return self.fresh_snapshot

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
        snapshotStable=True,
        creator={"account": "alice"},
    )


def unstable_snapshot(**changes: object) -> BugSnapshot:
    values: dict[str, object] = {
        "id": 7,
        "status": "active",
        "assignee": "alice",
        "title": "Broken button",
        "priority": "2",
        "creator": {"account": "alice"},
        "snapshotStable": False,
    }
    values.update(changes)
    return BugSnapshot(**values)


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


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("id", 8),
        ("status", "closed"),
        ("assignee", "bob"),
        ("title", "Different bug"),
        ("priority", "1"),
    ],
)
def test_unstable_snapshot_guard_rejects_safety_field_drift(
    field: str, changed: object
) -> None:
    before = unstable_snapshot()
    assert unstable_snapshot_matches(before, before.model_copy())
    assert not unstable_snapshot_matches(
        before, before.model_copy(update={field: changed})
    )


def test_snapshot_guard_uses_versions_when_either_snapshot_is_stable() -> None:
    stable = snapshot().model_copy(update={"snapshot_stable": True})
    assert unstable_snapshot_matches(stable, stable.model_copy())
    assert not unstable_snapshot_matches(
        stable, stable.model_copy(update={"snapshot_version": "v2"})
    )


@pytest.mark.parametrize(
    ("field", "changed"),
    [("status", "closed"), ("title", "Different bug")],
)
def test_stable_guard_requires_safety_fields_even_when_version_matches(
    field: str, changed: object
) -> None:
    stable = snapshot()
    assert not unstable_snapshot_matches(
        stable, stable.model_copy(update={field: changed})
    )


def test_mixed_stability_guard_requires_fields_and_matching_version() -> None:
    stable = snapshot()
    mixed = stable.model_copy(update={"snapshot_stable": False})
    assert unstable_snapshot_matches(stable, mixed)
    assert not unstable_snapshot_matches(
        stable, mixed.model_copy(update={"title": "Different bug"})
    )


def test_unstable_comment_requeries_before_write_and_fails_closed_on_drift() -> None:
    before = unstable_snapshot()
    provider = RecordingProvider(
        fresh_snapshot=before.model_copy(update={"title": "Changed title"})
    )
    ledger = RecordingLedger()
    from zentao_ai.workflows.comments import canonical_resolution_comment

    body = canonical_resolution_comment("candidate")
    authorized = context(
        provider,
        ledger,
        snapshotStable=False,
        authorizationRecords=(
            AuthorizationRecord(
                turnId="turn",
                source="user",
                action="comment",
                bugId="7",
                parameters={"comment": body},
            ),
        ),
    )

    result = write_resolution_comment(authorized, before, "candidate")

    assert result.status == "UNSTABLE_SNAPSHOT_CHANGED"
    assert provider.calls == [("query", 7, True)]
    assert [call[0] for call in ledger.calls] == ["put"]


def test_unstable_comment_requeries_immediately_before_write_when_unchanged() -> None:
    before = unstable_snapshot()
    events: list[str] = []

    class OrderedProvider(RecordingProvider):
        def query_bug_detail(
            self, bug_id: int | str, *, allow_unstable: bool = False
        ) -> BugSnapshot:
            events.append("query")
            return super().query_bug_detail(
                bug_id, allow_unstable=allow_unstable
            )

        def add_bug_comment(self, *args: object) -> CommentWriteResult:
            events.append("write")
            return super().add_bug_comment(*args)

    class OrderedLedger(RecordingLedger):
        def put_outbox(self, record: OutboxRecord) -> OutboxRecord:
            events.append("outbox")
            return super().put_outbox(record)

    provider = OrderedProvider(fresh_snapshot=before.model_copy())
    ledger = OrderedLedger()
    from zentao_ai.workflows.comments import canonical_resolution_comment

    body = canonical_resolution_comment("candidate")
    authorized = context(
        provider,
        ledger,
        snapshotStable=False,
        authorizationRecords=(
            AuthorizationRecord(
                turnId="turn",
                source="user",
                action="comment",
                bugId="7",
                parameters={"comment": body},
            ),
        ),
    )

    result = write_resolution_comment(authorized, before, "candidate")

    assert result.status == "CREATED"
    assert provider.calls[0] == ("query", 7, True)
    assert provider.calls[1][0] == "write"
    assert events == ["outbox", "query", "write"]


def test_claimed_stable_comment_cannot_bypass_actual_unstable_guard() -> None:
    before = unstable_snapshot()
    provider = RecordingProvider(
        fresh_snapshot=before.model_copy(update={"assignee": "mallory"})
    )
    ledger = RecordingLedger()
    from zentao_ai.workflows.comments import canonical_resolution_comment

    body = canonical_resolution_comment("candidate")
    authorized = context(
        provider,
        ledger,
        snapshotStable=True,
        authorizationRecords=(
            AuthorizationRecord(
                turnId="turn",
                source="user",
                action="comment",
                bugId="7",
                parameters={"comment": body},
            ),
        ),
    )

    result = write_resolution_comment(authorized, before, "candidate")

    assert result.status == "UNSTABLE_SNAPSHOT_CHANGED"
    assert not any(call[0] == "write" for call in provider.calls)
