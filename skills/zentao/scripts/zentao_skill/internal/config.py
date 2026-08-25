
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .errors import ConfigError


@dataclass(frozen=True)
class Config:
    base_url: str
    account: str
    password: str


def encode_env_value(value: str) -> str:
    """Encode one value using the small, symmetric dotenv grammar we support."""
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ConfigError(".env 值不能包含 NUL 或换行")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def decode_env_value(value: str, *, line_no: int) -> str:
    """Decode quoted dotenv values without invoking a shell parser."""
    if len(value) < 2 or value[0] != value[-1] or value[0] not in {"'", '"'}:
        return value.strip()
    if value[0] == "'":
        return value[1:-1]

    decoded: list[str] = []
    index = 1
    while index < len(value) - 1:
        character = value[index]
        if character != "\\":
            decoded.append(character)
            index += 1
            continue
        if index + 1 >= len(value) - 1 or value[index + 1] not in {'"', "\\"}:
            raise ConfigError(".env 包含不支持的转义", {"line": line_no})
        decoded.append(value[index + 1])
        index += 2
    return "".join(decoded)


def project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "skills" / "zentao" / "scripts" / "zentao.py").is_file():
            return parent
    raise ConfigError("无法从 Skill 脚本位置定位项目根目录")


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(".env 包含无法解析的行", {"line": line_no})
        key, value = line.split("=", 1)
        key = key.strip()
        value = decode_env_value(value, line_no=line_no)
        values[key] = value
    return values


def load_config() -> Config:
    file_values = parse_env(project_root() / ".env")
    def get(name: str, *, normalize: bool = False) -> str:
        value = os.environ.get(name, file_values.get(name, ""))
        if value == "":
            raise ConfigError(f"缺少必需配置 {name}")
        return value.strip() if normalize else value
    base_url = get("ZENTAO_BASE_URL", normalize=True).rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("ZENTAO_BASE_URL 必须是 http/https URL")
    return Config(base_url=base_url, account=get("ZENTAO_ACCOUNT", normalize=True), password=get("ZENTAO_PASSWORD"))
