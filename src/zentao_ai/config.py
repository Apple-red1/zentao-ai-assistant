from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import ValidationError

from zentao_ai.models import Settings

SECRET_KEY_PARTS = ("password", "token", "cookie", "authorization")


class ConfigError(ValueError):
    """Raised when local configuration is missing or invalid."""


def default_config_path() -> Path:
    override = os.environ.get("ZENTAO_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".codex" / "zentao-ai-bug" / "config.yaml"


def _contains_secret_key(value: object, prefix: str = "") -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            dotted = f"{prefix}.{key_text}" if prefix else key_text
            if any(part in key_text.casefold() for part in SECRET_KEY_PARTS):
                return dotted
            found = _contains_secret_key(child, dotted)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found = _contains_secret_key(child, f"{prefix}[{index}]")
            if found:
                return found
    return None


def load_settings(path: Path | None = None) -> Settings:
    config_path = (path or default_config_path()).expanduser()
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Configuration file not found: {config_path}") from exc
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Unable to read configuration: {config_path}") from exc

    if not isinstance(raw, Mapping):
        raise ConfigError("Configuration must be a YAML mapping")
    secret_key = _contains_secret_key(raw)
    if secret_key:
        raise ConfigError(f"Forbidden secret field in configuration: {secret_key}")
    try:
        return Settings.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError("Invalid configuration; check fields and value types") from exc


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    config_path = (path or default_config_path()).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = yaml.safe_dump(
        settings.model_dump(mode="json"),
        allow_unicode=True,
        sort_keys=False,
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=config_path.parent,
            prefix=f".{config_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            os.chmod(temporary_path, 0o600)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, config_path)
        os.chmod(config_path, 0o600)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return config_path


def redact(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: (
                "<redacted>"
                if any(part in str(key).casefold() for part in SECRET_KEY_PARTS)
                else redact(child)
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [redact(child) for child in value]
    if isinstance(value, tuple):
        return tuple(redact(child) for child in value)
    return value

