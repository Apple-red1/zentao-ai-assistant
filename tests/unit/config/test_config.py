from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from zentao_ai.config import load_config, migrate_config, redact_config, validate_config


def write_yaml(path: Path, data: object) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def minimal() -> dict[str, object]:
    return {
        "configVersion": 1,
        "personal": {"scopeNames": ["example-personal"]},
        "team": {"scopeNames": ["example-team"], "members": []},
        "repositories": {
            "example-personal": {
                "repository": "example-repo",
                "path": "repos/example-personal",
                "targetBranch": "main",
                "testCommands": ["pytest"],
            },
            "example-team": {
                "repository": "example-repo",
                "path": "repos/example-team",
                "targetBranch": "main",
                "testCommands": ["pytest"],
            },
        },
    }


def test_load_applies_safe_defaults(tmp_path: Path) -> None:
    config = load_config(write_yaml(tmp_path / "project.yaml", minimal()))
    assert config.permissions.model_dump() == {
        "codeWriteEnabled": False,
        "commentEnabled": False,
        "stepUpdateEnabled": False,
    }
    assert config.schedule.timezone == "Asia/Shanghai"
    assert config.schedule.time == "08:00"
    assert config.schedule.includeWeekends is True


def test_load_deep_merges_mappings_and_replaces_lists(tmp_path: Path) -> None:
    team = minimal()
    team["reporting"] = {"outputDirectory": "team", "formats": ["json", "md"]}
    project = {"configVersion": 1, "reporting": {"formats": ["json"]}}
    config = load_config(
        write_yaml(tmp_path / "project.yaml", project),
        write_yaml(tmp_path / "team.yaml", team),
    )
    assert config.reporting.outputDirectory == "team"
    assert config.reporting.formats == ["json"]


def test_migrates_unversioned_config_and_rejects_future_version() -> None:
    old = minimal()
    del old["configVersion"]
    assert migrate_config(old)["configVersion"] == 1
    with pytest.raises(ValueError, match="unsupported configVersion"):
        migrate_config({"configVersion": 2})


def test_validation_returns_field_errors_and_redacted_data(tmp_path: Path) -> None:
    data = minimal()
    data["personal"] = {"scopeNames": []}
    result = validate_config(write_yaml(tmp_path / "bad.yaml", data))
    assert result.valid is False
    assert result.configVersion == 1
    assert "personal.scopeNames" in {error.field for error in result.errors}
    assert result.redactedConfig is not None


def test_every_scope_has_exactly_one_repository_mapping(tmp_path: Path) -> None:
    data = minimal()
    data["repositories"] = {"example-personal": data["repositories"]["example-personal"]}  # type: ignore[index]
    result = validate_config(write_yaml(tmp_path / "bad.yaml", data))
    assert "repositories.example-team" in {error.field for error in result.errors}


@pytest.mark.parametrize("secret", ["plain-text", "${lower_case}", "${TOKEN}-suffix"])
def test_plaintext_secrets_are_rejected(tmp_path: Path, secret: str) -> None:
    data = minimal()
    data["zentao"] = {"password": secret}
    result = validate_config(write_yaml(tmp_path / "bad.yaml", data))
    assert "zentao.password" in {error.field for error in result.errors}


def test_environment_secret_references_are_allowed(tmp_path: Path) -> None:
    data = minimal()
    data["zentao"] = {"baseUrl": "https://zentao.example.invalid", "token": "${ZENTAO_TOKEN}"}
    assert validate_config(write_yaml(tmp_path / "valid.yaml", data)).valid


def test_redaction_is_recursive_case_insensitive_and_non_mutating() -> None:
    original = {
        "Password": "one",
        "nested": [{"apiToken": "two", "safe": "yes"}],
        "authorizationHeader": "three",
    }
    snapshot = deepcopy(original)
    assert redact_config(original) == {
        "Password": "***REDACTED***",
        "nested": [{"apiToken": "***REDACTED***", "safe": "yes"}],
        "authorizationHeader": "***REDACTED***",
    }
    assert original == snapshot
