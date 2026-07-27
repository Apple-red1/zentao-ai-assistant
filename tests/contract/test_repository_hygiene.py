from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SENSITIVE_CANDIDATES = (
    ".codex/zentao-ai-bug.yaml",
    ".codex/example.local-backup",
    ".env",
    ".env.production",
    "reports/daily.md",
    "state/checkpoint.json",
    "ledger/events.jsonl",
    "outbox/pending.json",
    "checkpoint.json",
    "runtime-checkpoint.json",
    "nested/runtime-checkpoint.json",
    "runtime-outbox.json",
    "nested/runtime-outbox.json",
    "data/cache.sqlite3",
    "session.cookie",
    "__pycache__/module.pyc",
    ".pytest_cache/state",
    "build/package.whl",
    "dist/package.tar.gz",
)

SENSITIVE_TRACKED_PATH = re.compile(
    r"(?:^|/)(?:reports|state|ledger|outbox)(?:/|$)"
    r"|(?:^|/)[^/]*(?:checkpoint|outbox)[^/]*(?:/|$)"
    r"|(?:^|/)\.codex/zentao-ai-bug\.yaml$"
    r"|(?:^|/)\.codex/[^/]+\.local-backup$"
    r"|(?:^|/)\.env[^/]*$"
    r"|\.(?:sqlite3|cookie)$",
    re.IGNORECASE,
)

PLAINTEXT_SECRET = re.compile(
    r"(?im)^\s*(?:password|cookie|token)\s*[:=]\s*"
    r"(?!['\"]?(?:|changeme|example|placeholder|redacted|\$\{[^}]+\})['\"]?\s*$)"
    r"\S+"
)

CONFIG_SUFFIXES = {".cfg", ".ini", ".json", ".toml", ".yaml", ".yml"}


def git(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def tracked_files() -> list[str]:
    result = git("ls-files")
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line]


def plaintext_secret_files() -> list[str]:
    findings: list[str] = []
    for relative_path in tracked_files():
        if Path(relative_path).suffix.lower() not in CONFIG_SUFFIXES:
            continue
        blob = git("show", "--no-textconv", f":{relative_path}")
        assert blob.returncode == 0, f"Unable to read index blob: {relative_path}"
        if PLAINTEXT_SECRET.search(blob.stdout):
            findings.append(relative_path)
    return findings


def test_sensitive_and_generated_paths_are_ignored() -> None:
    result = git(
        "check-ignore",
        "--no-index",
        "-z",
        "--stdin",
        input_text="\0".join(SENSITIVE_CANDIDATES) + "\0",
    )

    ignored = {path for path in result.stdout.split("\0") if path}
    assert ignored == set(SENSITIVE_CANDIDATES), result.stderr


def test_sensitive_paths_are_not_tracked() -> None:
    sensitive = [path for path in tracked_files() if SENSITIVE_TRACKED_PATH.search(path)]
    assert sensitive == []


def test_sensitive_path_detection_covers_checkpoint_and_outbox_names() -> None:
    paths = (
        "checkpoint.json",
        "nested/runtime-checkpoint.json",
        "runtime-outbox.json",
        "nested/runtime-outbox.json",
    )
    assert all(SENSITIVE_TRACKED_PATH.search(path) for path in paths)


def test_tracked_configuration_has_no_plaintext_secrets() -> None:
    assert plaintext_secret_files() == []


def test_plaintext_secret_scan_reads_the_index_blob(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(__import__(__name__), "ROOT", tmp_path)
    assert git("init", "-b", "main").returncode == 0

    config = tmp_path / "config.yaml"
    config.write_text("token: ${ZENTAO_TOKEN}\n", encoding="utf-8")
    assert git("add", "config.yaml").returncode == 0

    config.write_text("token: worktree-only-secret\n", encoding="utf-8")
    assert plaintext_secret_files() == []
