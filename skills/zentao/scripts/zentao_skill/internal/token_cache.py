from __future__ import annotations

import hashlib
import json
import os
import stat
import time
from pathlib import Path

from .config import Config, ensure_private_directory, resolve_runtime_paths, write_private_text_atomic
from .errors import ConfigError


DEFAULT_TOKEN_CACHE_TTL_SECONDS = 8 * 60 * 60


class TokenCache:
    """Short-lived on-disk ZenTao token cache scoped by base URL and account."""

    def __init__(self, *, root: Path | None = None, ttl_seconds: int = DEFAULT_TOKEN_CACHE_TTL_SECONDS) -> None:
        override = os.environ.get("ZENTAO_TOKEN_CACHE_DIR")
        self._uses_default_root = root is None and not override
        self.root = Path(override) if root is None and override else (root or resolve_runtime_paths().token_cache_root)
        self.ttl_seconds = max(0, int(ttl_seconds))

    def path_for(self, config: Config) -> Path:
        scope = hashlib.sha256(f"{config.base_url}\0{config.account}".encode("utf-8")).hexdigest()[:24]
        return self.root / f"token-{scope}.json"

    def load(self, config: Config) -> str | None:
        self._validate_root_location()
        path = self.path_for(config)
        if not path.is_file() or path.is_symlink():
            return None
        if os.name == "posix":
            try:
                root_mode = stat.S_IMODE(path.parent.stat().st_mode)
                file_mode = stat.S_IMODE(path.stat().st_mode)
            except OSError as exc:
                raise ConfigError("无法验证 Token cache 权限") from exc
            if root_mode != 0o700 or file_mode != 0o600:
                raise ConfigError("Token cache 权限不安全", {"directory_mode": oct(root_mode), "file_mode": oct(file_mode)})
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            token = payload.get("token")
            cached_at = float(payload.get("cached_at"))
        except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
            self.clear(config)
            return None
        if (
            payload.get("version") != 1
            or payload.get("base_url") != config.base_url
            or payload.get("account") != config.account
            or not isinstance(token, str)
            or not token
            or self.ttl_seconds == 0
            or time.time() - cached_at >= self.ttl_seconds
        ):
            self.clear(config)
            return None
        return token

    def store(self, config: Config, token: str) -> None:
        if self.ttl_seconds == 0 or not token:
            return
        self._ensure_private_dir()
        payload = {
            "version": 1,
            "base_url": config.base_url,
            "account": config.account,
            "cached_at": time.time(),
            "token": token,
        }
        write_private_text_atomic(
            self.path_for(config),
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
            label="Token cache",
        )

    def clear(self, config: Config) -> None:
        self._validate_root_location()
        try:
            self.path_for(config).unlink(missing_ok=True)
        except OSError:
            pass

    def _validate_root_location(self) -> None:
        if self.root.is_symlink():
            raise ConfigError("Token cache 目录不能是符号链接")
        if self._uses_default_root:
            runtime_paths = resolve_runtime_paths()
            expected_root = runtime_paths.token_cache_root
            if self.root != expected_root:
                raise ConfigError("默认 Token cache 路径与当前 runtime scope 不一致")
            anchor = runtime_paths.temp_root.parent
            try:
                current = self.root
                # Keep both paths lexical: system aliases above the runtime root
                # (e.g. macOS /var) are not links inside our private data tree.
                current.relative_to(anchor)
                while True:
                    if current.is_symlink():
                        raise ConfigError("默认 Token cache 路径不能包含符号链接")
                    if current == anchor:
                        break
                    current = current.parent
            except (OSError, ValueError) as exc:
                raise ConfigError("默认 Token cache 必须位于当前 runtime 数据目录下") from exc

    def _ensure_private_dir(self) -> None:
        self._validate_root_location()
        if self._uses_default_root and resolve_runtime_paths().scope == "user":
            ensure_private_directory(self.root.parents[1])
            ensure_private_directory(self.root.parent)
        ensure_private_directory(self.root)
