from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from zentao_ai.config import ConfigError, load_settings, redact, save_settings
from zentao_ai.models import Settings, TeamMember, TeamSettings, ZentaoSettings


def test_config_never_accepts_plaintext_password(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "version: 1\nzentao:\n  base_url: https://z.example\n"
        "  account: me\n  password: secret\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="password"):
        load_settings(path)


def test_settings_round_trip_with_private_permissions(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "config.yaml"
    settings = Settings(
        version=1,
        zentao=ZentaoSettings(base_url="https://z.example/", account="me"),
        team=TeamSettings(members=[TeamMember(name="张三", account="zhangsan")]),
    )

    saved = save_settings(settings, path)

    assert saved == path
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert load_settings(path) == settings


def test_environment_can_override_config_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "custom.yaml"
    save_settings(
        Settings(
            version=1,
            zentao=ZentaoSettings(base_url="https://z.example", account="me"),
        ),
        path,
    )
    monkeypatch.setenv("ZENTAO_CONFIG", str(path))

    assert load_settings().zentao.account == "me"


def test_redact_recursively_masks_secret_fields() -> None:
    value = {
        "account": "me",
        "token": "abc",
        "nested": [{"Authorization": "Token abc"}, {"cookie_value": "x"}],
    }

    assert redact(value) == {
        "account": "me",
        "token": "<redacted>",
        "nested": [
            {"Authorization": "<redacted>"},
            {"cookie_value": "<redacted>"},
        ],
    }
