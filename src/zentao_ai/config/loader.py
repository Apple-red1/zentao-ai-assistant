from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError as PydanticValidationError

from .migrations import migrate_config
from .models import AppConfig, ValidationError, ValidationResult
from .redaction import SENSITIVE_FRAGMENTS, redact_config

ENV_REFERENCE = re.compile(r"^\$\{[A-Z][A-Z0-9_]*\}$")


def _read(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise ValueError("configuration must be a mapping")
    return migrate_config(loaded)


def _merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _custom_errors(data: Mapping[str, Any]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    scopes: list[str] = []
    for section in ("personal", "team"):
        value = data.get(section)
        if isinstance(value, Mapping) and isinstance(value.get("scopeNames"), list):
            scopes.extend(str(item) for item in value["scopeNames"])
    repositories = data.get("repositories")
    repository_keys = set(repositories) if isinstance(repositories, Mapping) else set()
    for scope in scopes:
        if scope not in repository_keys:
            errors.append(ValidationError(field=f"repositories.{scope}", message="repository mapping is required"))
    for key in repository_keys - set(scopes):
        errors.append(ValidationError(field=f"repositories.{key}", message="repository does not match a scope"))

    def inspect(value: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                key_text = str(key)
                current = (*path, key_text)
                if any(part in key_text.lower() for part in SENSITIVE_FRAGMENTS):
                    if item is not None and (not isinstance(item, str) or not ENV_REFERENCE.fullmatch(item)):
                        errors.append(ValidationError(field=".".join(current), message="secret must use ${UPPER_SNAKE_CASE}"))
                else:
                    inspect(item, current)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                inspect(item, (*path, str(index)))

    inspect(data)
    return errors


def _parse(data: Mapping[str, Any]) -> AppConfig:
    custom = _custom_errors(data)
    if custom:
        raise ValueError("; ".join(f"{error.field}: {error.message}" for error in custom))
    return AppConfig.model_validate(data)


def load_config(project_path: Path, team_path: Path | None = None) -> AppConfig:
    data: dict[str, Any] = {"configVersion": 1}
    if team_path is not None:
        data = _merge(data, _read(team_path))
    data = _merge(data, _read(project_path))
    return _parse(data)


def validate_config(path: Path) -> ValidationResult:
    data: dict[str, Any] | None = None
    errors: list[ValidationError] = []
    version: int | None = None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError("configuration must be a mapping")
        data = migrate_config(raw)
        version_value = data.get("configVersion")
        version = version_value if type(version_value) is int else None
        errors.extend(_custom_errors(data))
        try:
            AppConfig.model_validate(data)
        except PydanticValidationError as exc:
            for item in exc.errors():
                errors.append(ValidationError(field=".".join(str(part) for part in item["loc"]), message=str(item["msg"])))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(ValidationError(field="configVersion" if "configVersion" in str(exc) else "config", message=str(exc)))
    return ValidationResult(
        valid=not errors,
        configVersion=version,
        errors=errors,
        redactedConfig=redact_config(data) if data is not None else None,
    )
