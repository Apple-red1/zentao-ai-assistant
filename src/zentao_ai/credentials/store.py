from __future__ import annotations

from enum import Enum
from typing import Protocol

import keyring
from pydantic import SecretStr

SERVICE_NAME = "zentao-ai-assistant"


class CredentialName(str, Enum):
    PASSWORD = "password"
    API_TOKEN = "api-token"
    WEB_COOKIE = "web-cookie"


class CredentialStoreError(RuntimeError):
    """A sanitized credential backend failure."""


class KeyringBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, password: str) -> None: ...

    def delete_password(self, service: str, username: str) -> None: ...


class CredentialReader(Protocol):
    def get(self, name: CredentialName) -> SecretStr | None: ...


class CredentialStore:
    def __init__(self, backend: KeyringBackend | None = None) -> None:
        self._backend = backend if backend is not None else keyring

    def get(self, name: CredentialName) -> SecretStr | None:
        try:
            value = self._backend.get_password(SERVICE_NAME, name.value)
        except Exception as exc:
            raise self._backend_error(name, exc) from None
        if value is None or not value.strip():
            return None
        return SecretStr(value)

    def set(self, name: CredentialName, value: SecretStr) -> None:
        plaintext = value.get_secret_value()
        if not plaintext.strip():
            raise ValueError(f"credential {name.value} must not be blank")
        try:
            self._backend.set_password(SERVICE_NAME, name.value, plaintext)
        except Exception as exc:
            raise self._backend_error(name, exc) from None

    def delete(self, name: CredentialName) -> None:
        try:
            self._backend.delete_password(SERVICE_NAME, name.value)
        except Exception as exc:
            raise self._backend_error(name, exc) from None

    @staticmethod
    def _backend_error(name: CredentialName, exc: Exception) -> CredentialStoreError:
        return CredentialStoreError(f"credential {name.value} backend error: {type(exc).__name__}")
