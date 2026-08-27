
from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from .errors import ConfigError


@dataclass(frozen=True)
class Config:
    base_url: str
    account: str
    password: str


RuntimeScope = Literal["project", "user"]


@dataclass(frozen=True)
class RuntimePaths:
    scope: RuntimeScope
    config_path: Path
    token_cache_root: Path
    temp_root: Path


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


def write_private_text_atomic(path: Path, content: str, *, label: str = ".env") -> None:
    """Write private text without exposing a partially written secret file."""
    fd: int | None = None
    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        if os.name == "posix" and stat.S_IMODE(os.fstat(fd).st_mode) != 0o600:
            raise ConfigError(f"{label} 临时文件未以 0600 权限创建")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "posix" and stat.S_IMODE(os.stat(temp_name).st_mode) != 0o600:
            raise ConfigError(f"{label} 临时文件权限不安全")
        os.replace(temp_name, path)
        temp_name = None
        if os.name == "posix" and stat.S_IMODE(os.stat(path).st_mode) != 0o600:
            raise ConfigError(f"{label} 文件权限不安全")
    except ConfigError:
        raise
    except (OSError, UnicodeError):
        raise ConfigError(f"无法安全写入 {label}")
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except OSError:
                pass


def project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "skills" / "zentao" / "scripts" / "zentao.py").is_file():
            return parent
    raise ConfigError("无法从 Skill 脚本位置定位项目根目录")


def _user_data_root() -> Path:
    return Path.home() / ".zentao-ai-assistant"


def paths_for_scope(scope: RuntimeScope) -> RuntimePaths:
    if scope == "project":
        root = project_root()
        return RuntimePaths(
            scope="project",
            config_path=root / ".env",
            token_cache_root=root / ".tmp" / "zentao" / "auth",
            temp_root=root / ".tmp",
        )
    if scope == "user":
        root = _user_data_root()
        return RuntimePaths(
            scope="user",
            config_path=root / "config.env",
            token_cache_root=root / "cache" / "auth",
            temp_root=root / "tmp",
        )
    raise ConfigError("运行 scope 必须是 project 或 user", {"scope": scope})


def _explicit_config_path(value: str) -> Path:
    if not value.strip():
        raise ConfigError("ZENTAO_CONFIG_FILE 不能为空")
    path = Path(value).expanduser()
    try:
        path = path.resolve(strict=False)
    except OSError as exc:
        raise ConfigError("无法解析显式配置文件路径") from exc
    if not path.is_file():
        raise ConfigError("显式配置文件不存在", {"path": str(path)})
    return path


def resolve_runtime_paths() -> RuntimePaths:
    explicit = os.environ.get("ZENTAO_CONFIG_FILE")
    if explicit is not None:
        config_path = _explicit_config_path(explicit)
        project_paths = paths_for_scope("project")
        if config_path == project_paths.config_path.resolve():
            return project_paths
        user_paths = paths_for_scope("user")
        return RuntimePaths(
            scope="user",
            config_path=config_path,
            token_cache_root=user_paths.token_cache_root,
            temp_root=user_paths.temp_root,
        )

    project_paths = paths_for_scope("project")
    if project_paths.config_path.is_file():
        return project_paths
    return paths_for_scope("user")


def ensure_private_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise ConfigError("私有运行目录必须是目录且不能是符号链接", {"path": str(path)})
        if os.name == "posix":
            path.chmod(0o700)
            if stat.S_IMODE(path.stat().st_mode) != 0o700:
                raise ConfigError("私有运行目录权限必须为 0700", {"path": str(path)})
    except ConfigError:
        raise
    except OSError as exc:
        raise ConfigError("无法安全创建私有运行目录", {"path": str(path)}) from exc


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ConfigError(".env 必须使用 UTF-8 编码", {"path": str(path), "encoding": "utf-8", "position": exc.start}) from exc
    except OSError as exc:
        raise ConfigError("无法读取配置文件", {"path": str(path)}) from exc
    for line_no, raw in enumerate(lines, 1):
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
    file_values = parse_env(resolve_runtime_paths().config_path)
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
