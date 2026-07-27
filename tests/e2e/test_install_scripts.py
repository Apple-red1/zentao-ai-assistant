from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def fake_environment(tmp_path: Path) -> tuple[dict[str, str], Path]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log = tmp_path / "commands.log"
    shim = "#!/bin/sh\nprintf '%s\\n' \"$0 $*\" >> \"$INSTALL_LOG\"\nexit 0\n"
    for name in ("python3", "python", "codex", "zentao-ai"):
        write_executable(fake_bin / name, shim)
    config = tmp_path / "config.yaml"
    config.write_text("version: 1\n", encoding="utf-8")
    environment = dict(os.environ)
    environment.update(
        {
            "PATH": f"{fake_bin}:/bin:/usr/bin",
            "INSTALL_LOG": str(log),
            "ZENTAO_CONFIG": str(config),
        }
    )
    return environment, log


def test_posix_installer_is_idempotent_and_non_interactive(tmp_path: Path) -> None:
    environment, log = fake_environment(tmp_path)
    command = ["/bin/sh", str(ROOT / "scripts" / "install.sh"), "--non-interactive"]

    first = subprocess.run(command, env=environment, text=True, capture_output=True, check=False)
    second = subprocess.run(command, env=environment, text=True, capture_output=True, check=False)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    calls = log.read_text(encoding="utf-8")
    assert "-m pipx install --force" in calls
    assert "plugin marketplace add" in calls
    assert "plugin add zentao-ai-bug@zentao-ai-assistant" in calls
    assert "zentao-ai doctor --config" in calls
    assert "password" not in first.stdout.casefold()


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell is not installed")
def test_powershell_installer_is_idempotent_and_non_interactive(tmp_path: Path) -> None:
    environment, log = fake_environment(tmp_path)
    command = [
        "pwsh",
        "-NoProfile",
        "-File",
        str(ROOT / "scripts" / "install.ps1"),
        "-NonInteractive",
    ]

    first = subprocess.run(command, env=environment, text=True, capture_output=True, check=False)
    second = subprocess.run(command, env=environment, text=True, capture_output=True, check=False)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    calls = log.read_text(encoding="utf-8")
    assert "-m pipx install --force" in calls
    assert "plugin marketplace add" in calls
    assert "plugin add zentao-ai-bug@zentao-ai-assistant" in calls
    assert "zentao-ai doctor --config" in calls
