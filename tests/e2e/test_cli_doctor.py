from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import zentao_ai.cli as cli


def test_doctor_returns_two_when_config_is_missing(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        cli.app,
        ["doctor", "--config", str(tmp_path / "missing.yaml")],
    )

    assert result.exit_code == 2
    assert "FAIL CONFIG" in result.output
    assert "password" not in result.output.casefold()
    assert "token" not in result.output.casefold()


def test_doctor_check_names_are_stable() -> None:
    assert cli.DOCTOR_CHECK_NAMES == (
        "CONFIG",
        "CREDENTIALS",
        "LOGIN",
        "API_V2",
        "TEAM_MEMBERS",
        "QUERY_MY_BUGS",
        "EDIT",
        "COMMENT",
        "ACTIVATE",
        "ASSIGN",
        "MCP",
    )

