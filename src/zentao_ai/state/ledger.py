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
    CliError,
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
                "SELECT * FROM leases WHERE business_date=? AND run_kind=? AND active=1",
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
            if row is not None:
                connection.execute(
                    "UPDATE leases SET active=0,status='EXPIRED' WHERE lease_id=?",
                    (row["lease_id"],),
                )
            connection.execute(
                "INSERT INTO leases VALUES(?,?,?,?,?,?,?,?,?,?)",
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
                    1,
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
                "UPDATE leases SET status=?, released_at=?, active=0 WHERE lease_id=? AND active=1",
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
                "SELECT * FROM core_outbox WHERE idempotency_key=?", (key,)
            ).fetchone()
            if row:
                if row["payload_hash"] != digest:
                    raise IdempotencyConflict(key)
                connection.commit()
                return self._outbox(row)
            connection.execute(
                "INSERT INTO core_outbox VALUES(?,?,?,?,?,?,?)",
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
                "SELECT * FROM core_outbox WHERE idempotency_key=?", (_key(key),)
            ).fetchone()
            if not row:
                raise KeyError(key)
            current = OutboxStatus(row["status"])
            terminal = {
                OutboxStatus.CREATED,
                OutboxStatus.ALREADY_EXISTS,
                OutboxStatus.FAILED,
            }
            if current in terminal:
                if status is current and not reconcile:
                    connection.commit()
                    return self._outbox(row)
                raise ValueError("terminal outbox state cannot transition")
            if current is OutboxStatus.UNKNOWN:
                if not reconcile:
                    raise ValueError("UNKNOWN requires explicit reconciliation")
                if status not in terminal:
                    raise ValueError(
                        "UNKNOWN reconciliation requires a terminal result"
                    )
            elif reconcile:
                raise ValueError("only UNKNOWN records can be reconciled")
            connection.execute(
                "UPDATE core_outbox SET status=?, external_id=? WHERE idempotency_key=?",
                (status.value, external_id, key),
            )
            connection.commit()
            return self._outbox(
                connection.execute(
                    "SELECT * FROM core_outbox WHERE idempotency_key=?", (key,)
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
                "INSERT INTO core_checkpoints VALUES(?,?,?,?) ON CONFLICT(business_date,run_kind) DO UPDATE SET payload_json=excluded.payload_json,updated_at=excluded.updated_at",
                (business_date.isoformat(), run_kind, rendered, now),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def get_checkpoint(self, business_date: date, run_kind: str) -> Any | None:
        row = self._connection.execute(
            "SELECT payload_json FROM core_checkpoints WHERE business_date=? AND run_kind=?",
            (business_date.isoformat(), run_kind),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def _legacy_lease(
        self,
        table: str,
        keys: dict[str, str],
        owner: str,
        ttl: int,
        business_date: str | None = None,
    ) -> dict[str, Any]:
        if ttl < 1 or ttl > 86400:
            raise CliError(
                "invalid_argument",
                "Lease duration must be between 1 and 86400 seconds.",
                "lease-seconds",
            )
        now = _now()
        now_text = _text(now)
        expires = _text(now + timedelta(seconds=ttl))
        where = " AND ".join(f"{name}=?" for name in keys)
        values = tuple(keys.values())
        connection = self._write()
        try:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE {where}", values
            ).fetchone()
            renewed = row is not None and row["owner"] == owner
            acquired = row is None or renewed or row["expires_at"] <= now_text
            if acquired:
                if row is None:
                    columns = [*keys, "owner", "expires_at"]
                    vals: list[str] = [*keys.values(), owner, expires]
                    if table == "job_leases":
                        columns += [
                            "business_date",
                            "status",
                            "acquired_at",
                            "updated_at",
                        ]
                        vals += [business_date or "", "active", now_text, now_text]
                    elif table == "repo_leases":
                        columns += ["updated_at"]
                        vals += [now_text]
                    marks = ",".join("?" for _ in vals)
                    connection.execute(
                        f"INSERT INTO {table}({','.join(columns)}) VALUES({marks})",
                        vals,
                    )
                else:
                    extras = (
                        ",business_date=?,status='active',updated_at=?"
                        if table == "job_leases"
                        else (",updated_at=?" if table == "repo_leases" else "")
                    )
                    extra_values: list[str] = (
                        [business_date or "", now_text]
                        if table == "job_leases"
                        else ([now_text] if table == "repo_leases" else [])
                    )
                    connection.execute(
                        f"UPDATE {table} SET owner=?,expires_at=?{extras} WHERE {where}",
                        (owner, expires, *extra_values, *values),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        labels = {"job_key": "jobKey", "bug_id": "bugId", "repo_key": "repoKey"}
        result: dict[str, Any] = {
            "acquired": acquired,
            "renewed": renewed if acquired else False,
            **{labels[k]: v for k, v in keys.items()},
            "owner": owner,
            "expiresAt": expires if acquired else row["expires_at"],
        }
        if not acquired:
            result["heldBy"] = row["owner"]
        return result

    def _legacy_release(
        self, table: str, keys: dict[str, str], owner: str
    ) -> dict[str, Any]:
        where = " AND ".join(f"{name}=?" for name in keys)
        values = tuple(keys.values())
        connection = self._write()
        try:
            row = connection.execute(
                f"SELECT owner FROM {table} WHERE {where}", values
            ).fetchone()
            field = (
                "bug-id"
                if "bug_id" in keys
                else ("repo-key" if "repo_key" in keys else "job-key")
            )
            if row is None:
                raise CliError("lease_not_found", "Lease does not exist.", field)
            if row["owner"] != owner:
                raise CliError(
                    "lease_owner_mismatch",
                    "Only the lease owner may release it.",
                    "owner",
                )
            if table == "job_leases":
                connection.execute(
                    f"UPDATE {table} SET status='released',expires_at=?,updated_at=? WHERE {where}",
                    (_text(_now()), _text(_now()), *values),
                )
            else:
                connection.execute(f"DELETE FROM {table} WHERE {where}", values)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        labels = {"job_key": "jobKey", "bug_id": "bugId", "repo_key": "repoKey"}
        return {
            "released": True,
            **{labels[k]: v for k, v in keys.items()},
            "owner": owner,
        }

    def acquire_job(
        self, job_key: str, owner: str, business_date: str, lease_seconds: int
    ) -> dict[str, Any]:
        date.fromisoformat(business_date)
        return self._legacy_lease(
            "job_leases", {"job_key": job_key}, owner, lease_seconds, business_date
        )

    def release_job(self, job_key: str, owner: str) -> dict[str, Any]:
        return self._legacy_release("job_leases", {"job_key": job_key}, owner)

    def acquire_bug(
        self, job_key: str, bug_id: str, owner: str, lease_seconds: int
    ) -> dict[str, Any]:
        return self._legacy_lease(
            "bug_leases", {"job_key": job_key, "bug_id": bug_id}, owner, lease_seconds
        )

    def release_bug(self, job_key: str, bug_id: str, owner: str) -> dict[str, Any]:
        return self._legacy_release(
            "bug_leases", {"job_key": job_key, "bug_id": bug_id}, owner
        )

    def acquire_repo(
        self, repo_key: str, owner: str, lease_seconds: int
    ) -> dict[str, Any]:
        return self._legacy_lease(
            "repo_leases", {"repo_key": repo_key}, owner, lease_seconds
        )

    def release_repo(self, repo_key: str, owner: str) -> dict[str, Any]:
        return self._legacy_release("repo_leases", {"repo_key": repo_key}, owner)

    def compat_checkpoint_put(
        self,
        job_key: str,
        bug_id: str,
        snapshot_version: str,
        stage: str,
        payload_raw: str,
    ) -> dict[str, Any]:
        payload = json.loads(payload_raw)
        rendered, _ = _payload(payload)
        updated = _text(_now())
        connection = self._write()
        try:
            connection.execute(
                "INSERT INTO legacy_checkpoints VALUES(?,?,?,?,?,?) ON CONFLICT(job_key,bug_id) DO UPDATE SET snapshot_version=excluded.snapshot_version,stage=excluded.stage,payload_json=excluded.payload_json,updated_at=excluded.updated_at",
                (job_key, bug_id, snapshot_version, stage, rendered, updated),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return {
            "stored": True,
            "checkpoint": {
                "jobKey": job_key,
                "bugId": bug_id,
                "snapshotVersion": snapshot_version,
                "stage": stage,
                "payload": payload,
                "updatedAt": updated,
            },
        }

    def compat_checkpoint_get(self, job_key: str, bug_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT * FROM legacy_checkpoints WHERE job_key=? AND bug_id=?",
            (job_key, bug_id),
        ).fetchone()
        if row is None:
            return {"found": False, "checkpoint": None}
        return {
            "found": True,
            "checkpoint": {
                "jobKey": row["job_key"],
                "bugId": row["bug_id"],
                "snapshotVersion": row["snapshot_version"],
                "stage": row["stage"],
                "payload": json.loads(row["payload_json"]),
                "updatedAt": row["updated_at"],
            },
        }

    def comment_put(
        self,
        idempotency_key: str,
        bug_id: str,
        snapshot_version: str,
        decision: str,
        comment_id: str | None,
        status: str,
    ) -> dict[str, Any]:
        updated = _text(_now())
        connection = self._write()
        try:
            row = connection.execute(
                "SELECT * FROM comment_records WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            created = row is None
            if row is None:
                connection.execute(
                    "INSERT INTO comment_records VALUES(?,?,?,?,?,?,?)",
                    (
                        idempotency_key,
                        bug_id,
                        snapshot_version,
                        decision,
                        comment_id,
                        status,
                        updated,
                    ),
                )
            else:
                if (row["bug_id"], row["snapshot_version"], row["decision"]) != (
                    bug_id,
                    snapshot_version,
                    decision,
                ):
                    raise CliError(
                        "idempotency_conflict",
                        "Idempotency key is already bound to a different comment identity.",
                        "idempotency-key",
                    )
                comment_id = comment_id if comment_id is not None else row["comment_id"]
                connection.execute(
                    "UPDATE comment_records SET comment_id=?,status=?,updated_at=? WHERE idempotency_key=?",
                    (comment_id, status, updated, idempotency_key),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return {
            "created": created,
            "idempotent": not created,
            "comment": {
                "idempotencyKey": idempotency_key,
                "bugId": bug_id,
                "snapshotVersion": snapshot_version,
                "decision": decision,
                "commentId": comment_id,
                "status": status,
                "updatedAt": updated,
            },
        }

    def comment_get(self, idempotency_key: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT * FROM comment_records WHERE idempotency_key=?", (idempotency_key,)
        ).fetchone()
        if row is None:
            return {"found": False, "comment": None}
        return {
            "found": True,
            "comment": {
                "idempotencyKey": row["idempotency_key"],
                "bugId": row["bug_id"],
                "snapshotVersion": row["snapshot_version"],
                "decision": row["decision"],
                "commentId": row["comment_id"],
                "status": row["status"],
                "updatedAt": row["updated_at"],
            },
        }

    def outbox_put(
        self, outbox_key: str, job_key: str, payload_raw: str
    ) -> dict[str, Any]:
        payload = json.loads(payload_raw)
        rendered, _ = _payload(payload)
        created_at = _text(_now())
        connection = self._write()
        try:
            row = connection.execute(
                "SELECT * FROM legacy_outbox WHERE outbox_key=?", (outbox_key,)
            ).fetchone()
            if row:
                if row["job_key"] != job_key or row["payload_json"] != rendered:
                    raise CliError(
                        "outbox_conflict",
                        "Outbox key is already bound to a different rendered payload.",
                        "outbox-key",
                    )
                connection.commit()
                return {
                    "created": False,
                    "idempotent": True,
                    "item": self._legacy_outbox_row(row),
                }
            connection.execute(
                "INSERT INTO legacy_outbox VALUES(?,?,?,'pending',0,NULL,?,NULL)",
                (outbox_key, job_key, rendered, created_at),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return {
            "created": True,
            "idempotent": False,
            "item": {
                "outboxKey": outbox_key,
                "jobKey": job_key,
                "payload": payload,
                "status": "pending",
                "attempts": 0,
                "lastError": None,
                "createdAt": created_at,
                "sentAt": None,
            },
        }

    def _legacy_outbox_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "outboxKey": row["outbox_key"],
            "jobKey": row["job_key"],
            "payload": json.loads(row["payload_json"]),
            "status": row["status"],
            "attempts": row["attempts"],
            "lastError": row["last_error"],
            "createdAt": row["created_at"],
            "sentAt": row["sent_at"],
        }

    def outbox_list(self, job_key: str | None, status: str | None) -> dict[str, Any]:
        sql = "SELECT * FROM legacy_outbox"
        clauses: list[str] = []
        values: list[str] = []
        if job_key is not None:
            clauses.append("job_key=?")
            values.append(job_key)
        if status is not None:
            clauses.append("status=?")
            values.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        rows = self._connection.execute(
            sql + " ORDER BY created_at,outbox_key", values
        ).fetchall()
        return {"items": [self._legacy_outbox_row(row) for row in rows]}

    def outbox_sent(self, outbox_key: str) -> dict[str, Any]:
        connection = self._write()
        try:
            row = connection.execute(
                "SELECT * FROM legacy_outbox WHERE outbox_key=?", (outbox_key,)
            ).fetchone()
            if row is None:
                raise CliError(
                    "outbox_not_found", "Outbox record does not exist.", "outbox-key"
                )
            idempotent = row["status"] == "sent"
            if not idempotent:
                connection.execute(
                    "UPDATE legacy_outbox SET status='sent',attempts=attempts+1,last_error=NULL,sent_at=? WHERE outbox_key=?",
                    (_text(_now()), outbox_key),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        return {"sent": True, "idempotent": idempotent, "outboxKey": outbox_key}
