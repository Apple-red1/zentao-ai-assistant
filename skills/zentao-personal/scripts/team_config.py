"""One local default team per authenticated site/account; no ZenTao writes."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path


class TeamError(ValueError):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def valid_account(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and value == value.strip()
            and not any(ord(c) < 32 for c in value) and value.casefold() != 'closed')


class TeamStore:
    def __init__(self, identity: dict[str, str]):
        if not valid_account(identity.get('account')):
            raise TeamError('TEAM_IDENTITY_INVALID', '无法确定团队所属账号')
        self.identity = dict(identity)
        key = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.root = Path.home() / '.zentao-ai-assistant'
        self.directory = self.root / 'teams'
        self.path = self.directory / f'{key}.json'

    def _check(self, *, create=False):
        for path in (self.root, self.directory):
            if path.is_symlink() or (path.exists() and not path.is_dir()):
                raise TeamError('TEAM_CONFIG_UNSAFE', '团队目录不能是符号链接或普通文件')
            if create:
                path.mkdir(mode=0o700, exist_ok=True)
                if os.name == 'posix':
                    path.chmod(0o700)
        if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
            raise TeamError('TEAM_CONFIG_UNSAFE', '团队配置必须是普通文件')

    def read(self) -> list[str]:
        self._check()
        try:
            fd = os.open(self.path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        except FileNotFoundError:
            return []
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1024 * 1024:
                raise TeamError('TEAM_CONFIG_UNSAFE', '团队配置类型或大小不安全')
            if os.name == 'posix' and stat.S_IMODE(info.st_mode) != 0o600:
                raise TeamError('TEAM_CONFIG_UNSAFE', '团队配置权限必须为 0600')
            with os.fdopen(fd, encoding='utf-8') as handle:
                fd = -1
                data = json.load(handle)
        except (ValueError, UnicodeError) as exc:
            if isinstance(exc, TeamError):
                raise
            raise TeamError('TEAM_CONFIG_INVALID', '团队配置损坏；未覆盖原文件') from exc
        finally:
            if fd >= 0:
                os.close(fd)
        if (not isinstance(data, dict) or type(data.get('schema_version')) is not int
                or data['schema_version'] != 1 or data.get('owner') != self.identity
                or not isinstance(data.get('members'), list)
                or any(not valid_account(a) for a in data['members'])
                or len(set(data['members'])) != len(data['members'])
                or self.identity['account'] in data['members']):
            raise TeamError('TEAM_CONFIG_INVALID', '团队配置版本、归属或成员无效；未覆盖原文件')
        return sorted(data['members'])

    def update(self, operation: str, accounts: list[str]) -> list[str]:
        if operation not in {'add', 'remove', 'replace'} or any(not valid_account(a) for a in accounts):
            raise TeamError('TEAM_INPUT_INVALID', '团队操作或账号无效')
        self._check(create=True)
        lock = self.path.with_suffix('.lock')
        try:
            lock.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise TeamError('TEAM_CONFIG_BUSY', '团队配置正在修改；未写入。若进程已退出，请人工检查锁目录') from exc
        temporary = None
        try:
            old = set(self.read())
            requested = set(accounts) - {self.identity['account']}
            members = sorted(old | requested if operation == 'add' else old - requested if operation == 'remove' else requested)
            data = {'schema_version': 1, 'owner': self.identity, 'members': members}
            fd, temporary = tempfile.mkstemp(prefix='.team-', dir=self.directory)
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                if os.name == 'posix':
                    os.fchmod(handle.fileno(), 0o600)
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
                handle.flush()
                os.fsync(handle.fileno())
            self._check()
            os.replace(temporary, self.path)
            temporary = None
            return members
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
            lock.rmdir()
