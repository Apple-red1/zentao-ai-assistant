"""Private, identity-scoped JSON storage for higher-level Skills.

The store deliberately owns only local user configuration. It never contains
ZenTao credentials and does not know anything about a particular Skill's
schema beyond the validator supplied by its caller.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


class IdentityStoreError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


ErrorFactory = Callable[[str, str, dict[str, object]], Exception]
Validator = Callable[[dict[str, Any]], None]


def normalize_connection_identity(identity: Mapping[str, object]) -> dict[str, str]:
    """Normalize a non-secret ZenTao base URL and account for storage keys."""
    raw_url = identity.get("base_url")
    raw_account = identity.get("account")
    if not isinstance(raw_url, str) or not isinstance(raw_account, str):
        raise IdentityStoreError("IDENTITY_INVALID", "配置所属身份无效")
    account = raw_account.strip()
    if not account or account != raw_account or any(ord(char) < 32 for char in account):
        raise IdentityStoreError("IDENTITY_INVALID", "配置所属账号无效")
    value = raw_url.strip()
    if "://" not in value:
        raise IdentityStoreError("IDENTITY_INVALID", "配置所属站点地址必须是不含凭据、查询或片段的 http/https 地址")
    scheme, remainder = value.split("://", 1)
    scheme = scheme.lower()
    if scheme not in {"http", "https"} or not remainder or "?" in remainder or "#" in remainder:
        raise IdentityStoreError("IDENTITY_INVALID", "配置所属站点地址必须是不含凭据、查询或片段的 http/https 地址")
    authority, path_separator, suffix = remainder.partition("/")
    if (not authority or "@" in authority or any(char.isspace() or ord(char) < 32 for char in authority)):
        raise IdentityStoreError("IDENTITY_INVALID", "配置所属站点地址必须是不含凭据、查询或片段的 http/https 地址")
    port: int | None = None
    if authority.startswith("["):
        closing = authority.find("]")
        if closing <= 1 or (authority[closing + 1:] and not authority[closing + 1:].startswith(":")):
            raise IdentityStoreError("IDENTITY_INVALID", "配置所属站点端口无效")
        host = authority[1:closing].lower()
        port_text = authority[closing + 2:] if authority[closing + 1:] else ""
    else:
        if authority.count(":") > 1:
            raise IdentityStoreError("IDENTITY_INVALID", "IPv6 地址必须使用方括号")
        host, _, port_text = authority.partition(":")
        host = host.lower()
    if not host or any(char.isspace() or ord(char) < 32 for char in host):
        raise IdentityStoreError("IDENTITY_INVALID", "配置所属站点主机无效")
    if port_text:
        if not port_text.isascii() or not port_text.isdigit():
            raise IdentityStoreError("IDENTITY_INVALID", "配置所属站点端口无效")
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise IdentityStoreError("IDENTITY_INVALID", "配置所属站点端口无效")
    default_port = {"http": 80, "https": 443}[scheme]
    host_display = f"[{host}]" if authority.startswith("[") else host
    if port is not None and port != default_port:
        host_display = f"{host_display}:{port}"
    path = f"/{suffix}" if path_separator else ""
    base_url = f"{scheme}://{host_display}{path.rstrip('/')}"
    return {"base_url": base_url, "account": account}


class IdentityScopedJsonStore:
    """A lock-protected JSON file keyed by normalized site and account."""

    def __init__(
        self,
        identity: Mapping[str, object],
        *,
        namespace: str,
        schema_version: int,
        max_bytes: int = 1024 * 1024,
        validator: Validator | None = None,
        root: Path | None = None,
        error_factory: ErrorFactory | None = None,
    ) -> None:
        if (not isinstance(namespace, str) or not namespace or namespace in {".", ".."}
                or any(char in namespace for char in "/\\\x00\r\n")):
            raise IdentityStoreError("NAMESPACE_INVALID", "配置命名空间无效")
        if type(schema_version) is not int or schema_version < 1:
            raise IdentityStoreError("SCHEMA_INVALID", "配置 schema 版本无效")
        if type(max_bytes) is not int or max_bytes < 1:
            raise IdentityStoreError("SIZE_INVALID", "配置大小上限无效")
        self.identity = normalize_connection_identity(identity)
        self.namespace = namespace
        self.schema_version = schema_version
        self.max_bytes = max_bytes
        self.validator = validator
        self.error_factory = error_factory
        self.root = Path(root).expanduser() if root is not None else Path.home() / ".zentao-ai-assistant"
        self.directory = self.root / namespace
        key = hashlib.sha256(json.dumps(
            self.identity, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        self.path = self.directory / f"{key}.json"
        self.lock_path = self.path.with_suffix(".lock")

    def _error(self, code: str, message: str, details: dict[str, object] | None = None) -> Exception:
        safe_details = details or {}
        if self.error_factory is not None:
            return self.error_factory(code, message, safe_details)
        return IdentityStoreError(code, message, safe_details)

    def _check_directory(self, path: Path, *, create: bool) -> None:
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise self._error("UNSAFE", "配置目录不能是符号链接或普通文件", {"path": str(path)})
        if not path.exists():
            if create:
                path.mkdir(mode=0o700)
            else:
                return
        if path.is_symlink() or not path.is_dir():
            raise self._error("UNSAFE", "配置目录必须是普通目录", {"path": str(path)})
        if os.name == "posix":
            path.chmod(0o700)
            if stat.S_IMODE(path.stat().st_mode) != 0o700:
                raise self._error("UNSAFE", "配置目录权限必须为 0700", {"path": str(path)})

    def _check_parent(self, *, create: bool) -> None:
        # Check each owned path before creating it, so a symlink cannot be
        # followed during mkdir(parents=True).
        self._check_directory(self.root, create=create)
        self._check_directory(self.directory, create=create)

    def _check_target(self) -> None:
        if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
            raise self._error("UNSAFE", "配置文件必须是普通文件", {"path": str(self.path)})

    def _validate(self, payload: object) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise self._error("INVALID", "配置根必须是 JSON 对象")
        if type(payload.get("schema_version")) is not int or payload.get("schema_version") != self.schema_version:
            raise self._error("INVALID", "配置 schema 版本不匹配")
        if payload.get("owner") != self.identity:
            raise self._error("INVALID", "配置所属身份不匹配")
        if self.validator is not None:
            self.validator(payload)
        return payload

    def read(self) -> dict[str, Any]:
        """Read the file, returning an empty object only when it is absent."""
        self._check_parent(create=False)
        self._check_target()
        try:
            fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        except FileNotFoundError:
            return {}
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > self.max_bytes:
                raise self._error("UNSAFE", "配置文件类型或大小不安全", {"path": str(self.path)})
            if os.name == "posix" and stat.S_IMODE(info.st_mode) != 0o600:
                raise self._error("UNSAFE", "配置文件权限必须为 0600", {"path": str(self.path)})
            with os.fdopen(fd, encoding="utf-8") as handle:
                fd = -1
                try:
                    payload = json.load(handle)
                except (json.JSONDecodeError, UnicodeError) as exc:
                    raise self._error("INVALID", "配置损坏；未覆盖原文件") from exc
        finally:
            if fd >= 0:
                os.close(fd)
        return self._validate(payload)

    def _acquire(self) -> None:
        if self.lock_path.is_symlink() or (self.lock_path.exists() and not self.lock_path.is_dir()):
            raise self._error("UNSAFE", "配置锁必须是普通目录", {"path": str(self.lock_path)})
        try:
            self.lock_path.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise self._error("BUSY", "配置正在修改；未写入。若进程已退出，请人工检查锁目录") from exc
        if os.name == "posix":
            self.lock_path.chmod(0o700)

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self._check_parent(create=True)
        self._check_target()
        encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if len(encoded.encode("utf-8")) > self.max_bytes:
            raise self._error("UNSAFE", "配置内容超过大小上限", {"path": str(self.path), "max_bytes": self.max_bytes})
        temporary: str | None = None
        fd: int | None = None
        try:
            fd, temporary = tempfile.mkstemp(prefix=f".{self.namespace}-", dir=str(self.directory))
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                fd = None
                if os.name == "posix":
                    os.fchmod(handle.fileno(), 0o600)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            self._check_target()
            os.replace(temporary, self.path)
            temporary = None
            if os.name == "posix":
                directory_fd = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            if os.name == "posix" and stat.S_IMODE(self.path.stat().st_mode) != 0o600:
                raise self._error("UNSAFE", "配置文件权限必须为 0600", {"path": str(self.path)})
        finally:
            if fd is not None:
                os.close(fd)
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    def update(self, transform: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        self._check_parent(create=True)
        self._acquire()
        try:
            current = self.read()
            updated = transform(current)
            self._validate(updated)
            self._atomic_write(updated)
            return updated
        finally:
            self.lock_path.rmdir()

    def replace(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._check_parent(create=True)
        self._acquire()
        try:
            self._validate(payload)
            self._atomic_write(payload)
            return payload
        finally:
            self.lock_path.rmdir()


__all__ = ["IdentityScopedJsonStore", "IdentityStoreError", "normalize_connection_identity"]
