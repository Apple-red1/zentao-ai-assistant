from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[2] / "scripts" / "run-ledger.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def test_init_outputs_utf8_json(tmp_path):
    result = run("--db", str(tmp_path / "账本.db"), "init")
    assert result.returncode == 0
    assert json.loads(result.stdout)["initialized"] is True
    assert "账本" in result.stdout


def test_validate_config_delegates_to_shared_config(tmp_path):
    config = tmp_path / "bad.yaml"
    config.write_text("configVersion: 999\n", encoding="utf-8")
    result = run("validate-config", "--config", str(config))
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["valid"] is False
    assert payload["errors"]


def test_legacy_checkpoint_commands_round_trip(tmp_path):
    db = tmp_path / "db"
    put = run(
        "--db",
        str(db),
        "checkpoint-put",
        "--job-key",
        "daily:2026-07-15",
        "--bug-id",
        "42",
        "--snapshot-version",
        "v1",
        "--stage",
        "分析",
        "--payload-json",
        '{"内容":"中文"}',
    )
    assert put.returncode == 0
    got = run(
        "--db",
        str(db),
        "checkpoint-get",
        "--job-key",
        "daily:2026-07-15",
        "--bug-id",
        "42",
    )
    assert json.loads(got.stdout)["checkpoint"]["payload"] == {"内容": "中文"}


def test_all_lease_commands_preserve_fields_and_renewal(tmp_path):
    db = str(tmp_path / "db")
    base = (
        "--db",
        db,
        "acquire-job",
        "--job-key",
        "daily",
        "--owner",
        "one",
        "--business-date",
        "2026-07-15",
        "--lease-seconds",
        "60",
    )
    assert json.loads(run(*base).stdout)["renewed"] is False
    assert json.loads(run(*base).stdout)["renewed"] is True
    denied = json.loads(
        run(
            "--db",
            db,
            "acquire-job",
            "--job-key",
            "daily",
            "--owner",
            "two",
            "--business-date",
            "2026-07-15",
            "--lease-seconds",
            "60",
        ).stdout
    )
    assert denied["acquired"] is False and denied["heldBy"] == "one"
    assert json.loads(
        run("--db", db, "release-job", "--job-key", "daily", "--owner", "one").stdout
    ) == {"jobKey": "daily", "owner": "one", "released": True}
    for kind, key_args, expected in (
        (
            "bug",
            ("--job-key", "daily", "--bug-id", "42"),
            {"jobKey": "daily", "bugId": "42"},
        ),
        ("repo", ("--repo-key", "repo"), {"repoKey": "repo"}),
    ):
        acquired = json.loads(
            run(
                "--db",
                db,
                f"acquire-{kind}",
                *key_args,
                "--owner",
                "one",
                "--lease-seconds",
                "60",
            ).stdout
        )
        assert acquired | expected == acquired
        released = json.loads(
            run("--db", db, f"release-{kind}", *key_args, "--owner", "one").stdout
        )
        assert released | expected == released


def test_comment_and_outbox_full_contract(tmp_path):
    db = str(tmp_path / "db")
    args = (
        "--db",
        db,
        "comment-put",
        "--idempotency-key",
        "c1",
        "--bug-id",
        "42",
        "--snapshot-version",
        "v1",
        "--decision",
        "fix",
        "--status",
        "created",
        "--comment-id",
        "9",
    )
    assert json.loads(run(*args).stdout)["created"] is True
    assert json.loads(run(*args).stdout)["idempotent"] is True
    assert (
        json.loads(run("--db", db, "comment-get", "--idempotency-key", "c1").stdout)[
            "comment"
        ]["commentId"]
        == "9"
    )
    out = (
        "--db",
        db,
        "outbox-put",
        "--outbox-key",
        "o1",
        "--job-key",
        "daily",
        "--payload-json",
        '{"text":"中文"}',
    )
    item = json.loads(run(*out).stdout)
    assert item["item"]["status"] == "pending" and item["item"]["attempts"] == 0
    assert json.loads(run(*out).stdout)["idempotent"] is True
    assert (
        json.loads(run("--db", db, "outbox-sent", "--outbox-key", "o1").stdout)[
            "idempotent"
        ]
        is False
    )
    assert (
        json.loads(run("--db", db, "outbox-sent", "--outbox-key", "o1").stdout)[
            "idempotent"
        ]
        is True
    )
    listed = json.loads(
        run("--db", db, "outbox-list", "--job-key", "daily", "--status", "sent").stdout
    )
    assert listed["items"][0]["attempts"] == 1 and listed["items"][0]["sentAt"]


def test_argparse_errors_are_structured_json():
    for args in (("acquire-job",), ("unknown-command",), ("init", "--unknown")):
        result = run(*args)
        assert result.returncode == 2
        assert json.loads(result.stdout) == {
            "ok": False,
            "error": {
                "code": "invalid_arguments",
                "message": "Invalid command arguments.",
            },
        }
