from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from zentao_ai.state import (
    CommentRecord,
    IdempotencyConflict,
    Ledger,
    OutboxRecord,
    OutboxStatus,
    PayloadRejected,
    RunStatus,
)


def test_schema_lease_and_expired_takeover(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    with Ledger(path) as ledger:
        first = ledger.acquire_lease(date(2026, 7, 15), "daily", "one", 60)
        denied = ledger.acquire_lease(date(2026, 7, 15), "daily", "two", 60)
        assert first.acquired and not denied.acquired
        ledger._connection.execute(
            "UPDATE leases SET expires_at='2000-01-01T00:00:00Z'"
        )
        takeover = ledger.acquire_lease(date(2026, 7, 15), "daily", "two", 60)
        assert takeover.acquired and takeover.previous_owner == "one"
        history = ledger._connection.execute(
            "SELECT lease_id,owner,status,active FROM leases ORDER BY acquired_at,lease_id"
        ).fetchall()
        assert len(history) == 2
        assert {row["lease_id"] for row in history} == {
            first.lease_id,
            takeover.lease_id,
        }
        assert any(
            row["owner"] == "one" and row["status"] == "EXPIRED" and row["active"] == 0
            for row in history
        )
        ledger.release_lease(takeover.lease_id, RunStatus.SUCCEEDED)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1


def test_comment_idempotency_uses_canonical_hash(tmp_path):
    with Ledger(tmp_path / "db") as ledger:
        with pytest.raises(ValueError):
            ledger.record_comment(CommentRecord(" key ", "42", {"b": 2}))
        original = ledger.record_comment(
            CommentRecord("key", "42", {"b": 2, "a": "text"})
        )
        same = ledger.record_comment(CommentRecord("key", "42", {"a": "text", "b": 2}))
        assert same.payload_hash == original.payload_hash
        with pytest.raises(IdempotencyConflict):
            ledger.record_comment(CommentRecord("key", "42", {"a": "different"}))


def test_outbox_unknown_requires_explicit_reconcile(tmp_path):
    with Ledger(tmp_path / "db") as ledger:
        ledger.put_outbox(OutboxRecord("send-1", "daily", {"message": "ok"}))
        unknown = ledger.mark_outbox_result("send-1", OutboxStatus.UNKNOWN, None)
        assert unknown.status is OutboxStatus.UNKNOWN
        with pytest.raises(ValueError):
            ledger.mark_outbox_result("send-1", OutboxStatus.CREATED, "1")
        reconciled = ledger.reconcile_outbox("send-1", OutboxStatus.CREATED, "1")
        assert reconciled.status is OutboxStatus.CREATED


@pytest.mark.parametrize(
    "terminal", [OutboxStatus.CREATED, OutboxStatus.ALREADY_EXISTS, OutboxStatus.FAILED]
)
def test_outbox_terminal_states_cannot_transition(tmp_path, terminal):
    with Ledger(tmp_path / "db") as ledger:
        ledger.put_outbox(OutboxRecord("send-1", "daily", {"message": "ok"}))
        ledger.mark_outbox_result("send-1", terminal, None)
        with pytest.raises(ValueError):
            ledger.mark_outbox_result("send-1", OutboxStatus.UNKNOWN, None)


@pytest.mark.parametrize("target", [OutboxStatus.PENDING, OutboxStatus.UNKNOWN])
def test_unknown_reconcile_only_accepts_terminal_target(tmp_path, target):
    with Ledger(tmp_path / "db") as ledger:
        ledger.put_outbox(OutboxRecord("send-1", "daily", {"message": "ok"}))
        ledger.mark_outbox_result("send-1", OutboxStatus.UNKNOWN, None)
        with pytest.raises(ValueError):
            ledger.reconcile_outbox("send-1", target, None)


def test_checkpoint_and_payload_protection(tmp_path):
    with Ledger(tmp_path / "db") as ledger:
        ledger.put_checkpoint(date(2026, 7, 15), "daily", {"cursor": [1, 2]})
        assert ledger.get_checkpoint(date(2026, 7, 15), "daily") == {"cursor": [1, 2]}
        with pytest.raises(PayloadRejected):
            ledger.put_checkpoint(date(2026, 7, 15), "secret", {"apiToken": "nope"})
        with pytest.raises(PayloadRejected):
            ledger.put_checkpoint(
                date(2026, 7, 15), "deep", {"x": [[[[[[[[[[1]]]]]]]]]]}
            )


def test_legacy_oversized_payload_has_exact_error(monkeypatch):
    from zentao_ai.state import ledger as state_ledger
    from zentao_ai.state.models import CliError

    monkeypatch.setattr(state_ledger, "MAX_PAYLOAD_BYTES", 8)
    with pytest.raises(CliError) as caught:
        state_ledger._legacy_payload('{"value":"too long"}')
    assert (caught.value.code, caught.value.field) == ("payload_too_large", "payload-json")


def test_migration_rolls_back_on_failure(tmp_path, monkeypatch):
    from zentao_ai.state import migrations

    path = tmp_path / "db"
    monkeypatch.setattr(
        migrations, "MIGRATIONS", ("CREATE TABLE partial(x); INVALID SQL",)
    )
    with pytest.raises(sqlite3.Error), Ledger(path):
        pass
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='partial'"
            ).fetchone()
            is None
        )
