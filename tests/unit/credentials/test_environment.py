from __future__ import annotations

import pytest

from zentao_ai.credentials import CredentialUnavailableError, resolve_environment_reference


def test_resolve_environment_reference_accepts_complete_reference() -> None:
    secret = resolve_environment_reference("${CUSTOM_SECRET}", {"CUSTOM_SECRET": "fixture-value"})
    assert secret.get_secret_value() == "fixture-value"


@pytest.mark.parametrize("value", ["prefix-${CUSTOM_SECRET}", "${lower}", "CUSTOM_SECRET", "${CUSTOM_SECRET}suffix"])
def test_resolve_environment_reference_rejects_non_complete_reference(value: str) -> None:
    with pytest.raises(ValueError, match="complete environment reference"):
        resolve_environment_reference(value, {"CUSTOM_SECRET": "fixture-value"})


@pytest.mark.parametrize("env", [{}, {"CUSTOM_SECRET": ""}, {"CUSTOM_SECRET": "  "}])
def test_resolve_environment_reference_rejects_missing_or_blank_value(env: dict[str, str]) -> None:
    with pytest.raises(CredentialUnavailableError, match="CUSTOM_SECRET"):
        resolve_environment_reference("${CUSTOM_SECRET}", env)
