from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

import zentao_ai.cli as cli


@dataclass
class FakeCredentialStore:
    password: str | None = None
    base_url: str | None = None
    account: str | None = None

    def set_password(self, base_url: str, account: str, password: str) -> None:
        self.base_url = base_url
        self.account = account
        self.password = password


def test_setup_writes_config_but_not_password(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FakeCredentialStore()
    monkeypatch.setattr(cli, "credential_store", lambda: store)
    config_path = tmp_path / "config.yaml"

    result = CliRunner().invoke(
        cli.app,
        ["setup", "--config", str(config_path)],
        input=(
            "https://z.example\n"
            "me\n"
            "secret\n"
            "张三=zhangsan,李四=lisi\n"
        ),
    )

    assert result.exit_code == 0, result.output
    text = config_path.read_text(encoding="utf-8")
    assert "secret" not in text
    assert "zhangsan" in text and "lisi" in text
    assert store.password == "secret"
    assert store.account == "me"

