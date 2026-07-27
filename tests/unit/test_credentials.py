from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from zentao_ai.credentials import KeyringCredentialStore


@dataclass
class FakeKeyring:
    values: dict[tuple[str, str], str] = field(default_factory=dict)

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, value: str) -> None:
        self.values[(service, username)] = value

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


def test_keyring_keys_are_scoped_by_url_and_account() -> None:
    backend = FakeKeyring()
    store = KeyringCredentialStore(backend=backend)

    store.set_password("https://z.example/", "me", "secret")

    assert store.get_password("https://z.example", "me") == "secret"
    assert store.get_password("https://other.example", "me") is None
    assert store.get_password("https://z.example", "other") is None


def test_password_uses_environment_only_when_keyring_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = FakeKeyring()
    store = KeyringCredentialStore(backend=backend)
    monkeypatch.setenv("ZENTAO_PASSWORD", "environment-secret")

    assert store.get_password("https://z.example", "me") == "environment-secret"

    store.set_password("https://z.example", "me", "keyring-secret")
    assert store.get_password("https://z.example", "me") == "keyring-secret"


def test_token_can_be_replaced_and_deleted() -> None:
    backend = FakeKeyring()
    store = KeyringCredentialStore(backend=backend)

    store.set_token("https://z.example", "me", "old")
    store.set_token("https://z.example", "me", "fresh")
    assert store.get_token("https://z.example", "me") == "fresh"

    store.delete_token("https://z.example", "me")
    assert store.get_token("https://z.example", "me") is None
