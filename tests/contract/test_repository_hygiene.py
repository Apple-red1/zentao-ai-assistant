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
    "data/cache.sqlite3",
    "session.cookie",
    "__pycache__/module.pyc",
    ".pytest_cache/state",
    "build/package.whl",
    "dist/package.tar.gz",
)

SENSITIVE_TRACKED_PATH = re.compile(
    r"(?:^|/)(?:reports|state|ledger|outbox)(?:/|$)"
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
        check=False,
    )


def tracked_files() -> list[str]:
    result = git("ls-files")
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line]


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


def test_tracked_configuration_has_no_plaintext_secrets() -> None:
    findings: list[str] = []
    for relative_path in tracked_files():
        path = ROOT / relative_path
        if path.suffix.lower() not in CONFIG_SUFFIXES or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if PLAINTEXT_SECRET.search(text):
            findings.append(relative_path)

    assert findings == []
