"""One local default team per authenticated site/account; no ZenTao writes."""
from __future__ import annotations

import os
from typing import Any

from zentao.identity_store import IdentityScopedJsonStore


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
        self._store = IdentityScopedJsonStore(
            identity,
            namespace='teams',
            schema_version=1,
            validator=self._validate,
            error_factory=self._store_error,
        )
        self.identity = dict(self._store.identity)
        self.root = self._store.root
        self.directory = self._store.directory
        self.path = self._store.path

    @staticmethod
    def _store_error(code: str, message: str, details: dict[str, object]) -> Exception:
        mapped = {'UNSAFE': 'TEAM_CONFIG_UNSAFE', 'INVALID': 'TEAM_CONFIG_INVALID',
                  'BUSY': 'TEAM_CONFIG_BUSY'}.get(code, 'TEAM_CONFIG_INVALID')
        return TeamError(mapped, message, details)

    def _validate(self, data: dict[str, Any]) -> None:
        if (not isinstance(data.get('members'), list)
                or any(not valid_account(account) for account in data['members'])
                or len(set(data['members'])) != len(data['members'])
                or self.identity['account'] in data['members']):
            raise TeamError('TEAM_CONFIG_INVALID', '团队配置版本、归属或成员无效；未覆盖原文件')

    def read(self) -> list[str]:
        data = self._store.read()
        if not data:
            return []
        return sorted(data['members'])

    def update(self, operation: str, accounts: list[str]) -> list[str]:
        if operation not in {'add', 'remove', 'replace'} or any(not valid_account(a) for a in accounts):
            raise TeamError('TEAM_INPUT_INVALID', '团队操作或账号无效')
        def transform(data: dict[str, Any]) -> dict[str, Any]:
            old = set(data.get('members', []))
            requested = set(accounts) - {self.identity['account']}
            members = sorted(old | requested if operation == 'add' else old - requested if operation == 'remove' else requested)
            return {'schema_version': 1, 'owner': self.identity, 'members': members}

        result = self._store.update(transform)
        return sorted(result['members'])
