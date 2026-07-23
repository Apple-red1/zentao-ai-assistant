from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from pydantic import SecretStr

from zentao_ai.credentials import CredentialName, CredentialUnavailableError, resolve_credential


@dataclass
class FakeReader:
    value: SecretStr | None = None
    reads: list[CredentialName] = field(default_factory=list)

    def get(self, name: CredentialName) -> SecretStr | None:
        self.reads.append(name)
        return self.value


@pytest.mark.parametrize(
    ("name", "env_name"),
    [
        (CredentialName.PASSWORD, "ZENTAO_PASSWORD"),
        (CredentialName.API_TOKEN, "ZENTAO_API_TOKEN"),
        (CredentialName.WEB_COOKIE, "ZENTAO_WEB_COOKIE"),
    ],
)
def test_resolve_credential_uses_expected_environment_name(name: CredentialName, env_name: str) -> None:
    result = resolve_credential(name, {env_name: "fixture-value"}, FakeReader())
    assert result.get_secret_value() == "fixture-value"


def test_resolve_credential_prefers_store_over_environment_and_prompt() -> None:
    prompted: list[CredentialName] = []
    result = resolve_credential(
        CredentialName.PASSWORD,
        {"ZENTAO_PASSWORD": "environment-value"},
        FakeReader(SecretStr("stored-value")),
        lambda name: prompted.append(name) or SecretStr("prompt-value"),
    )
    assert result.get_secret_value() == "stored-value"
    assert prompted == []


def test_resolve_credential_prompts_only_after_store_and_environment_are_missing() -> None:
    reader = FakeReader()
    prompted: list[CredentialName] = []
    result = resolve_credential(
        CredentialName.API_TOKEN,
        {},
        reader,
        lambda name: prompted.append(name) or SecretStr("prompt-value"),
    )
    assert result.get_secret_value() == "prompt-value"
    assert reader.reads == [CredentialName.API_TOKEN]
    assert prompted == [CredentialName.API_TOKEN]


@pytest.mark.parametrize("prompt_value", [None, SecretStr(""), SecretStr("  ")])
def test_resolve_credential_raises_when_all_sources_are_missing(prompt_value: SecretStr | None) -> None:
    with pytest.raises(CredentialUnavailableError, match="password"):
        resolve_credential(CredentialName.PASSWORD, {}, FakeReader(), lambda _: prompt_value)
