from __future__ import annotations

import os
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

import keyring
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError

SERVICE_NAME = "zentao-ai-bug"


class CredentialStore(Protocol):
    def get_password(self, base_url: str, account: str) -> str | None: ...

    def set_password(self, base_url: str, account: str, password: str) -> None: ...

    def get_token(self, base_url: str, account: str) -> str | None: ...

    def set_token(self, base_url: str, account: str, token: str) -> None: ...

    def delete_token(self, base_url: str, account: str) -> None: ...


def normalize_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url.strip())
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.casefold(), parsed.netloc.casefold(), path, "", ""))


class KeyringCredentialStore:
    def __init__(self, backend: KeyringBackend | None = None) -> None:
        self._backend = backend or keyring.get_keyring()

    @staticmethod
    def _key(kind: str, base_url: str, account: str) -> str:
        return f"{kind}:{normalize_base_url(base_url)}:{account.strip()}"

    def get_password(self, base_url: str, account: str) -> str | None:
        stored = self._backend.get_password(
            SERVICE_NAME,
            self._key("password", base_url, account),
        )
        return stored or os.environ.get("ZENTAO_PASSWORD")

    def set_password(self, base_url: str, account: str, password: str) -> None:
        self._backend.set_password(
            SERVICE_NAME,
            self._key("password", base_url, account),
            password,
        )

    def get_token(self, base_url: str, account: str) -> str | None:
        return self._backend.get_password(
            SERVICE_NAME,
            self._key("token", base_url, account),
        )

    def set_token(self, base_url: str, account: str, token: str) -> None:
        self._backend.set_password(
            SERVICE_NAME,
            self._key("token", base_url, account),
            token,
        )

    def delete_token(self, base_url: str, account: str) -> None:
        try:
            self._backend.delete_password(
                SERVICE_NAME,
                self._key("token", base_url, account),
            )
        except PasswordDeleteError:
            return
