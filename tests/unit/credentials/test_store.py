from __future__ import annotations

from typing import cast

import pytest
from pydantic import SecretStr

from zentao_ai.credentials import CredentialName, CredentialStore, CredentialStoreError
from zentao_ai.credentials.store import KeyringBackend


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}
        self.error: Exception | None = None

    def get_password(self, service: str, username: str) -> str | None:
        if self.error:
            raise self.error
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        if self.error:
            raise self.error
        self.values[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        if self.error:
            raise self.error
        self.values.pop((service, username), None)


def test_store_round_trip_and_delete_use_fixed_service() -> None:
    backend = FakeKeyring()
    store = CredentialStore(backend=backend)
    secret = SecretStr("fixture-value")

    store.set(CredentialName.API_TOKEN, secret)

    assert backend.values[("zentao-ai-assistant", "api-token")] == secret.get_secret_value()
    assert store.get(CredentialName.API_TOKEN) == secret
    store.delete(CredentialName.API_TOKEN)
    assert store.get(CredentialName.API_TOKEN) is None


@pytest.mark.parametrize("value", ["", " ", "\t\n"])
def test_store_rejects_blank_secrets(value: str) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        CredentialStore(backend=FakeKeyring()).set(CredentialName.PASSWORD, SecretStr(value))


def test_store_treats_blank_backend_value_as_missing() -> None:
    backend = FakeKeyring()
    backend.values[("zentao-ai-assistant", "password")] = "  "
    assert CredentialStore(backend=backend).get(CredentialName.PASSWORD) is None


@pytest.mark.parametrize("operation", ["get", "set", "delete"])
def test_store_sanitizes_backend_errors(operation: str) -> None:
    backend = FakeKeyring()
    backend.error = RuntimeError("fixture-value must never escape")
    store = CredentialStore(backend=backend)

    with pytest.raises(CredentialStoreError) as captured:
        if operation == "get":
            store.get(CredentialName.WEB_COOKIE)
        elif operation == "set":
            store.set(CredentialName.WEB_COOKIE, SecretStr("fixture-value"))
        else:
            store.delete(CredentialName.WEB_COOKIE)

    message = str(captured.value)
    assert message == "credential web-cookie backend error: RuntimeError"
    assert "fixture-value" not in message


def test_secret_repr_is_redacted() -> None:
    backend = FakeKeyring()
    backend.values[("zentao-ai-assistant", "password")] = "fixture-value"
    secret = CredentialStore(backend=cast(KeyringBackend, backend)).get(CredentialName.PASSWORD)
    assert secret is not None
    assert "fixture-value" not in repr(secret)
    assert "fixture-value" not in str(secret)
