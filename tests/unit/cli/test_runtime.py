from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from zentao_ai.cli import runtime
from zentao_ai.credentials import (
    CredentialName,
    CredentialStoreError,
    CredentialUnavailableError,
)


class ProviderCaptured(Exception):
    pass


def _capture_production_auth(monkeypatch: pytest.MonkeyPatch, tmp_path, resolver):
    captured = {}
    config = SimpleNamespace(
        zentao=SimpleNamespace(baseUrl="https://zentao.invalid", account="alice")
    )
    monkeypatch.setattr(runtime, "load_config", lambda path: config)
    monkeypatch.setattr(runtime, "CredentialStore", lambda: object())
    monkeypatch.setattr(runtime, "resolve_credential", resolver)

    def capture(**kwargs):
        captured.update(kwargs)
        raise ProviderCaptured

    monkeypatch.setattr(runtime, "HttpZentaoProvider", capture)
    with pytest.raises(ProviderCaptured):
        runtime.DependencyFactory._production(tmp_path)
    return captured


def test_production_runtime_falls_back_to_password_and_configures_login(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    calls = []

    def resolve(name, env, store):
        calls.append(name)
        if name is CredentialName.API_TOKEN:
            raise CredentialUnavailableError("api-token unavailable")
        return SecretStr("password-secret")

    captured = _capture_production_auth(monkeypatch, tmp_path, resolve)

    assert calls == [CredentialName.API_TOKEN, CredentialName.PASSWORD]
    assert captured["auth"].api_token is None
    assert captured["auth"].password.get_secret_value() == "password-secret"
    assert captured["endpoints"].login == "/api.php/v2/users/login"
    assert captured["endpoints"].products == "/api.php/v2/products"
    assert (
        captured["endpoints"].product_bugs == "/api.php/v2/products/{product_id}/bugs"
    )
    assert captured["endpoints"].global_bugs == "/api.php/v2/bugs"
    assert captured["endpoints"].bug_history == "/api.php/v2/bugs/{bug_id}"


def test_production_runtime_does_not_mask_api_token_backend_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    def resolve(name, env, store):
        raise CredentialStoreError("backend failure")

    with pytest.raises(CredentialStoreError, match="backend failure"):
        _capture_production_auth(monkeypatch, tmp_path, resolve)
