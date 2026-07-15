from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any

from zentao_ai.config import validate_config

from .ledger import Ledger, default_ledger_path
from .models import CommentRecord, OutboxRecord, OutboxStatus, RunStatus, StateError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--db", default=str(default_ledger_path()))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    validate = commands.add_parser("validate-config")
    validate.add_argument("--config", required=True)
    acquire = commands.add_parser("acquire-job")
    for name in ("job-key", "owner", "business-date"):
        acquire.add_argument(f"--{name}", required=True)
    acquire.add_argument("--lease-seconds", required=True, type=int)
    release = commands.add_parser("release-job")
    release.add_argument("--job-key", required=True)
    release.add_argument("--owner", required=True)
    for command in ("acquire-bug", "acquire-repo"):
        item = commands.add_parser(command)
        item.add_argument(
            "--job-key" if command.endswith("bug") else "--repo-key", required=True
        )
        if command.endswith("bug"):
            item.add_argument("--bug-id", required=True)
        item.add_argument("--owner", required=True)
        item.add_argument("--lease-seconds", required=True, type=int)
    for command in ("release-bug", "release-repo"):
        item = commands.add_parser(command)
        item.add_argument(
            "--job-key" if command.endswith("bug") else "--repo-key", required=True
        )
        if command.endswith("bug"):
            item.add_argument("--bug-id", required=True)
        item.add_argument("--owner", required=True)
    put = commands.add_parser("checkpoint-put")
    for name in ("job-key", "bug-id", "snapshot-version", "stage", "payload-json"):
        put.add_argument(f"--{name}", required=True)
    get = commands.add_parser("checkpoint-get")
    get.add_argument("--job-key", required=True)
    get.add_argument("--bug-id", required=True)
    comment = commands.add_parser("comment-put")
    for name in ("idempotency-key", "bug-id", "snapshot-version", "decision", "status"):
        comment.add_argument(f"--{name}", required=True)
    comment.add_argument("--comment-id")
    comment_get = commands.add_parser("comment-get")
    comment_get.add_argument("--idempotency-key", required=True)
    outbox = commands.add_parser("outbox-put")
    outbox.add_argument("--outbox-key", required=True)
    outbox.add_argument("--job-key", required=True)
    outbox.add_argument("--payload-json", required=True)
    listed = commands.add_parser("outbox-list")
    listed.add_argument("--job-key")
    listed.add_argument("--status")
    sent = commands.add_parser("outbox-sent")
    sent.add_argument("--outbox-key", required=True)
    return parser


def _legacy_date(job_key: str) -> date:
    try:
        return date.fromisoformat(job_key.rsplit(":", 1)[-1])
    except ValueError:
        return date.today()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def dispatch(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    if args.command == "validate-config":
        validation = validate_config(Path(args.config))
        return (0 if validation.valid else 2), _jsonable(validation)
    with Ledger(Path(args.db)) as ledger:
        if args.command == "init":
            return 0, {"initialized": True, "db": str(ledger.path)}
        if args.command == "acquire-job":
            lease = ledger.acquire_lease(
                date.fromisoformat(args.business_date),
                args.job_key,
                args.owner,
                args.lease_seconds,
            )
            return 0, {
                "acquired": lease.acquired,
                "renewed": False,
                "jobKey": args.job_key,
                "owner": args.owner,
                "heldBy": lease.previous_owner,
                "expiresAt": lease.expires_at,
            }
        if args.command == "release-job":
            row = ledger._connection.execute(
                "SELECT lease_id FROM leases WHERE run_kind=? AND owner=?",
                (args.job_key, args.owner),
            ).fetchone()
            if not row:
                raise ValueError("lease not found")
            ledger.release_lease(row[0], RunStatus.SUCCEEDED)
            return 0, {"released": True, "jobKey": args.job_key, "owner": args.owner}
        if args.command in {"acquire-bug", "acquire-repo"}:
            key = (
                f"bug:{args.job_key}:{args.bug_id}"
                if args.command.endswith("bug")
                else f"repo:{args.repo_key}"
            )
            lease = ledger.acquire_lease(
                date.today(), key, args.owner, args.lease_seconds
            )
            return 0, {
                "acquired": lease.acquired,
                "renewed": False,
                "owner": args.owner,
                "expiresAt": lease.expires_at,
            }
        if args.command in {"release-bug", "release-repo"}:
            key = (
                f"bug:{args.job_key}:{args.bug_id}"
                if args.command.endswith("bug")
                else f"repo:{args.repo_key}"
            )
            row = ledger._connection.execute(
                "SELECT lease_id FROM leases WHERE run_kind=? AND owner=?",
                (key, args.owner),
            ).fetchone()
            if not row:
                raise ValueError("lease not found")
            ledger.release_lease(row[0], RunStatus.SUCCEEDED)
            return 0, {"released": True, "owner": args.owner}
        if args.command == "checkpoint-put":
            payload = json.loads(args.payload_json)
            kind = f"legacy:{args.job_key}:{args.bug_id}"
            ledger.put_checkpoint(
                _legacy_date(args.job_key),
                kind,
                {
                    "snapshotVersion": args.snapshot_version,
                    "stage": args.stage,
                    "payload": payload,
                },
            )
            return 0, {
                "stored": True,
                "checkpoint": {
                    "jobKey": args.job_key,
                    "bugId": args.bug_id,
                    "snapshotVersion": args.snapshot_version,
                    "stage": args.stage,
                    "payload": payload,
                },
            }
        if args.command == "checkpoint-get":
            value = ledger.get_checkpoint(
                _legacy_date(args.job_key), f"legacy:{args.job_key}:{args.bug_id}"
            )
            return 0, {
                "found": value is not None,
                "checkpoint": (
                    {"jobKey": args.job_key, "bugId": args.bug_id, **value}
                    if value
                    else None
                ),
            }
        if args.command == "comment-put":
            payload = {
                "snapshotVersion": args.snapshot_version,
                "decision": args.decision,
                "commentId": args.comment_id,
                "status": args.status,
            }
            comment_record = ledger.record_comment(
                CommentRecord(args.idempotency_key, args.bug_id, payload)
            )
            return 0, {
                "stored": True,
                "record": {
                    "idempotencyKey": comment_record.idempotency_key,
                    "bugId": comment_record.bug_id,
                    **comment_record.payload,
                },
            }
        if args.command == "comment-get":
            found_comment = ledger.get_comment(args.idempotency_key)
            return 0, {
                "found": found_comment is not None,
                "record": (
                    {
                        "idempotencyKey": found_comment.idempotency_key,
                        "bugId": found_comment.bug_id,
                        **found_comment.payload,
                    }
                    if found_comment
                    else None
                ),
            }
        if args.command == "outbox-put":
            outbox_record = ledger.put_outbox(
                OutboxRecord(
                    args.outbox_key, args.job_key, json.loads(args.payload_json)
                )
            )
            return 0, {
                "stored": True,
                "outbox": {
                    "outboxKey": outbox_record.idempotency_key,
                    "jobKey": outbox_record.run_kind,
                    "payload": outbox_record.payload,
                    "status": outbox_record.status.value,
                },
            }
        if args.command == "outbox-sent":
            outbox_result = ledger.mark_outbox_result(
                args.outbox_key, OutboxStatus.CREATED, None
            )
            return 0, {"marked": True, "outboxKey": outbox_result.idempotency_key}
        if args.command == "outbox-list":
            query, params = "SELECT * FROM outbox WHERE 1=1", []
            if args.job_key:
                query += " AND run_kind=?"
                params.append(args.job_key)
            if args.status:
                query += " AND status=?"
                params.append(args.status)
            rows = ledger._connection.execute(query, params).fetchall()
            return 0, {
                "items": [
                    {
                        "outboxKey": row["idempotency_key"],
                        "jobKey": row["run_kind"],
                        "payload": json.loads(row["payload_json"]),
                        "status": row["status"],
                    }
                    for row in rows
                ]
            }
    raise ValueError("unknown command")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        code, payload = dispatch(_parser().parse_args(argv))
    except (ValueError, KeyError, StateError, json.JSONDecodeError) as error:
        code, payload = (
            2,
            {"ok": False, "error": {"code": "invalid_argument", "message": str(error)}},
        )
    except (sqlite3.Error, OSError):
        code, payload = (
            3,
            {
                "ok": False,
                "error": {
                    "code": "storage_error",
                    "message": "The local coordination store operation failed.",
                },
            },
        )
    print(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    return code
