from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Never

from zentao_ai.config import validate_config

from .ledger import Ledger, default_ledger_path
from .models import CliError, StateError


class JsonArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("add_help", False)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> Never:
        raise CliError("invalid_arguments", "Invalid command arguments.")


def _parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(add_help=False)
    parser.add_argument("--db", default=str(default_ledger_path()))
    commands = parser.add_subparsers(
        dest="command", required=True, parser_class=JsonArgumentParser
    )
    commands.add_parser("init")
    validate = commands.add_parser("validate-config")
    validate.add_argument("--config", required=True)
    job = commands.add_parser("acquire-job")
    for name in ("job-key", "owner", "business-date"):
        job.add_argument(f"--{name}", required=True)
    job.add_argument("--lease-seconds", required=True, type=int)
    release = commands.add_parser("release-job")
    release.add_argument("--job-key", required=True)
    release.add_argument("--owner", required=True)
    bug = commands.add_parser("acquire-bug")
    for name in ("job-key", "bug-id", "owner"):
        bug.add_argument(f"--{name}", required=True)
    bug.add_argument("--lease-seconds", required=True, type=int)
    release_bug = commands.add_parser("release-bug")
    for name in ("job-key", "bug-id", "owner"):
        release_bug.add_argument(f"--{name}", required=True)
    repo = commands.add_parser("acquire-repo")
    repo.add_argument("--repo-key", required=True)
    repo.add_argument("--owner", required=True)
    repo.add_argument("--lease-seconds", required=True, type=int)
    release_repo = commands.add_parser("release-repo")
    release_repo.add_argument("--repo-key", required=True)
    release_repo.add_argument("--owner", required=True)
    checkpoint = commands.add_parser("checkpoint-put")
    for name in ("job-key", "bug-id", "snapshot-version", "stage", "payload-json"):
        checkpoint.add_argument(f"--{name}", required=True)
    checkpoint_get = commands.add_parser("checkpoint-get")
    checkpoint_get.add_argument("--job-key", required=True)
    checkpoint_get.add_argument("--bug-id", required=True)
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
    outbox_list = commands.add_parser("outbox-list")
    outbox_list.add_argument("--job-key")
    outbox_list.add_argument("--status")
    outbox_sent = commands.add_parser("outbox-sent")
    outbox_sent.add_argument("--outbox-key", required=True)
    return parser


def dispatch(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    if args.command == "validate-config":
        result = validate_config(Path(args.config))
        return (0 if result.valid else 2), result.model_dump(mode="json")
    with Ledger(Path(args.db)) as ledger:
        command = args.command
        if command == "init":
            return 0, {"initialized": True, "db": str(ledger.path)}
        if command == "acquire-job":
            return 0, ledger.acquire_job(
                args.job_key, args.owner, args.business_date, args.lease_seconds
            )
        if command == "release-job":
            return 0, ledger.release_job(args.job_key, args.owner)
        if command == "acquire-bug":
            return 0, ledger.acquire_bug(
                args.job_key, args.bug_id, args.owner, args.lease_seconds
            )
        if command == "release-bug":
            return 0, ledger.release_bug(args.job_key, args.bug_id, args.owner)
        if command == "acquire-repo":
            return 0, ledger.acquire_repo(args.repo_key, args.owner, args.lease_seconds)
        if command == "release-repo":
            return 0, ledger.release_repo(args.repo_key, args.owner)
        if command == "checkpoint-put":
            return 0, ledger.compat_checkpoint_put(
                args.job_key,
                args.bug_id,
                args.snapshot_version,
                args.stage,
                args.payload_json,
            )
        if command == "checkpoint-get":
            return 0, ledger.compat_checkpoint_get(args.job_key, args.bug_id)
        if command == "comment-put":
            return 0, ledger.comment_put(
                args.idempotency_key,
                args.bug_id,
                args.snapshot_version,
                args.decision,
                args.comment_id,
                args.status,
            )
        if command == "comment-get":
            return 0, ledger.comment_get(args.idempotency_key)
        if command == "outbox-put":
            return 0, ledger.outbox_put(
                args.outbox_key, args.job_key, args.payload_json
            )
        if command == "outbox-list":
            return 0, ledger.outbox_list(args.job_key, args.status)
        if command == "outbox-sent":
            return 0, ledger.outbox_sent(args.outbox_key)
    raise CliError("unknown_command", "Unknown command.")


def _error(error: CliError) -> dict[str, Any]:
    details: dict[str, Any] = {"code": error.code, "message": error.message}
    if error.field is not None:
        details["field"] = error.field
    return {"ok": False, "error": details}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        code, payload = dispatch(_parser().parse_args(argv))
    except CliError as error:
        code, payload = 2, _error(error)
    except (ValueError, KeyError, StateError, json.JSONDecodeError) as error:
        code, payload = 2, _error(CliError("invalid_argument", str(error)))
    except (sqlite3.Error, OSError):
        code, payload = (
            3,
            _error(
                CliError(
                    "storage_error", "The local coordination store operation failed."
                )
            ),
        )
    except Exception:
        code, payload = (
            3,
            _error(CliError("internal_error", "The ledger command failed safely.")),
        )
    print(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    return code
