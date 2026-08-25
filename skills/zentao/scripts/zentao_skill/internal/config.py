
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
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def load_config() -> Config:
    file_values = parse_env(project_root() / ".env")
    def get(name: str) -> str:
        value = os.environ.get(name, file_values.get(name, "")).strip()
        if not value:
            raise ConfigError(f"缺少必需配置 {name}")
        return value
    base_url = get("ZENTAO_BASE_URL").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("ZENTAO_BASE_URL 必须是 http/https URL")
    return Config(base_url=base_url, account=get("ZENTAO_ACCOUNT"), password=get("ZENTAO_PASSWORD"))
