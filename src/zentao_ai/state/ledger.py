from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from platformdirs import user_data_path

from .migrations import migrate
from .models import (
    CommentRecord,
    IdempotencyConflict,
    LeaseResult,
    OutboxRecord,
    OutboxStatus,
    PayloadRejected,
    RunStatus,
)

MAX_PAYLOAD_BYTES = 1_048_576
MAX_PAYLOAD_DEPTH = 8
SENSITIVE = (
    "token",
    "password",
    "secret",
    "apikey",
    "authorization",
    "cookie",
    "credential",
)


def default_ledger_path() -> Path:
    return user_data_path("zentao-ai-assistant") / "run-ledger.sqlite3"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _key(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("idempotency key must be non-empty")
    return value


def _payload(value: Any, depth: int = 0) -> tuple[str, str]:
    if depth > MAX_PAYLOAD_DEPTH:
        raise PayloadRejected("payload nesting is too deep")
    if value is None or isinstance(value, (str, bool, int, float)):
        pass
    elif isinstance(value, list):
        for item in value:
            _payload(item, depth + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PayloadRejected("object keys must be strings")
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if any(part in normalized for part in SENSITIVE):
                raise PayloadRejected("secret-like fields cannot be persisted")
            _payload(item, depth + 1)
    else:
        raise PayloadRejected("payload is not JSON-safe")
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise PayloadRejected("payload is not JSON-safe") from exc
    if len(rendered.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise PayloadRejected("payload is too large")
    return rendered, hashlib.sha256(rendered.encode("utf-8")).hexdigest()


class Ledger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = (path or default_ledger_path()).expanduser().resolve()
        self._connection: sqlite3.Connection

    def __enter__(self) -> "Ledger":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA busy_timeout=5000")
        self._connection.execute("PRAGMA journal_mode=WAL")
        migrate(self._connection)
        return self

    def __exit__(self, *_args: object) -> None:
        self._connection.close()

    def _write(self) -> sqlite3.Connection:
        self._connection.execute("BEGIN IMMEDIATE")
        return self._connection

    def acquire_lease(
        self, business_date: date, run_kind: str, owner: str, ttl_seconds: int
    ) -> LeaseResult:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        now, lease_id = _now(), str(uuid.uuid4())
        expires = _text(now + timedelta(seconds=ttl_seconds))
        connection = self._write()
        try:
            row = connection.execute(
                "SELECT * FROM leases WHERE business_date=? AND run_kind=?",
                (business_date.isoformat(), run_kind),
            ).fetchone()
            if (
                row is not None
                and row["status"] == RunStatus.ACTIVE.value
                and row["expires_at"] > _text(now)
            ):
                connection.commit()
                return LeaseResult(
                    False, row["lease_id"], owner, row["expires_at"], row["owner"]
                )
            previous = row["owner"] if row else None
            connection.execute(
                "DELETE FROM leases WHERE business_date=? AND run_kind=?",
                (business_date.isoformat(), run_kind),
            )
            connection.execute(
                "INSERT INTO leases VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    lease_id,
                    business_date.isoformat(),
                    run_kind,
                    owner,
                    RunStatus.ACTIVE.value,
                    _text(now),
                    expires,
                    None,
                    previous,
                ),
            )
            connection.commit()
            return LeaseResult(True, lease_id, owner, expires, previous)
        except Exception:
            connection.rollback()
            raise

    def release_lease(self, lease_id: str, status: RunStatus) -> None:
        if status is RunStatus.ACTIVE:
            raise ValueError("release status must be terminal")
        connection = self._write()
        try:
            cursor = connection.execute(
                "UPDATE leases SET status=?, released_at=? WHERE lease_id=?",
                (status.value, _text(_now()), lease_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(lease_id)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def record_comment(self, record: CommentRecord) -> CommentRecord:
        key = _key(record.idempotency_key)
        rendered, digest = _payload(record.payload)
        now = _text(_now())
        connection = self._write()
        try:
            row = connection.execute(
                "SELECT * FROM comments WHERE idempotency_key=?", (key,)
            ).fetchone()
            if row:
                if row["payload_hash"] != digest:
                    raise IdempotencyConflict(key)
                connection.commit()
                return self._comment(row)
            connection.execute(
                "INSERT INTO comments VALUES(?,?,?,?,?)",
                (key, record.bug_id, rendered, digest, now),
            )
            connection.commit()
            return replace(
                record, idempotency_key=key, payload_hash=digest, created_at=now
            )
        except Exception:
            connection.rollback()
            raise

    def _comment(self, row: sqlite3.Row) -> CommentRecord:
        return CommentRecord(
            row["idempotency_key"],
            row["bug_id"],
            json.loads(row["payload_json"]),
            row["payload_hash"],
            row["created_at"],
        )

    def get_comment(self, idempotency_key: str) -> CommentRecord | None:
        row = self._connection.execute(
            "SELECT * FROM comments WHERE idempotency_key=?", (_key(idempotency_key),)
        ).fetchone()
        return self._comment(row) if row else None

    def put_outbox(self, record: OutboxRecord) -> OutboxRecord:
        key = _key(record.idempotency_key)
        rendered, digest = _payload(record.payload)
        now = _text(_now())
        connection = self._write()
        try:
            row = connection.execute(
                "SELECT * FROM outbox WHERE idempotency_key=?", (key,)
            ).fetchone()
            if row:
                if row["payload_hash"] != digest:
                    raise IdempotencyConflict(key)
                connection.commit()
                return self._outbox(row)
            connection.execute(
                "INSERT INTO outbox VALUES(?,?,?,?,?,?,?)",
                (
                    key,
                    record.run_kind,
                    rendered,
                    digest,
                    OutboxStatus.PENDING.value,
                    None,
                    now,
                ),
            )
            connection.commit()
            return replace(
                record, idempotency_key=key, payload_hash=digest, created_at=now
            )
        except Exception:
            connection.rollback()
            raise

    def _outbox(self, row: sqlite3.Row) -> OutboxRecord:
        return OutboxRecord(
            row["idempotency_key"],
            row["run_kind"],
            json.loads(row["payload_json"]),
            OutboxStatus(row["status"]),
            row["external_id"],
            row["payload_hash"],
            row["created_at"],
        )

    def mark_outbox_result(
        self, idempotency_key: str, status: OutboxStatus, external_id: str | None
    ) -> OutboxRecord:
        return self._set_outbox(idempotency_key, status, external_id, False)

    def reconcile_outbox(
        self, idempotency_key: str, status: OutboxStatus, external_id: str | None
    ) -> OutboxRecord:
        return self._set_outbox(idempotency_key, status, external_id, True)

    def _set_outbox(
        self, key: str, status: OutboxStatus, external_id: str | None, reconcile: bool
    ) -> OutboxRecord:
        connection = self._write()
        try:
            row = connection.execute(
                "SELECT * FROM outbox WHERE idempotency_key=?", (_key(key),)
            ).fetchone()
            if not row:
                raise KeyError(key)
            if row["status"] == OutboxStatus.UNKNOWN.value and not reconcile:
                raise ValueError("UNKNOWN requires explicit reconciliation")
            connection.execute(
                "UPDATE outbox SET status=?, external_id=? WHERE idempotency_key=?",
                (status.value, external_id, key),
            )
            connection.commit()
            return self._outbox(
                connection.execute(
                    "SELECT * FROM outbox WHERE idempotency_key=?", (key,)
                ).fetchone()
            )
        except Exception:
            connection.rollback()
            raise

    def put_checkpoint(self, business_date: date, run_kind: str, payload: Any) -> None:
        rendered, _ = _payload(payload)
        now = _text(_now())
        connection = self._write()
        try:
            connection.execute(
                "INSERT INTO checkpoints VALUES(?,?,?,?) ON CONFLICT(business_date,run_kind) DO UPDATE SET payload_json=excluded.payload_json,updated_at=excluded.updated_at",
                (business_date.isoformat(), run_kind, rendered, now),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def get_checkpoint(self, business_date: date, run_kind: str) -> Any | None:
        row = self._connection.execute(
            "SELECT payload_json FROM checkpoints WHERE business_date=? AND run_kind=?",
            (business_date.isoformat(), run_kind),
        ).fetchone()
        return json.loads(row[0]) if row else None
