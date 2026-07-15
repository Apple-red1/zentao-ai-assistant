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
