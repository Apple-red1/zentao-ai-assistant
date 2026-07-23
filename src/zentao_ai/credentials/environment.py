from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from pydantic import SecretStr

from .store import CredentialName, CredentialReader

_REFERENCE = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")
_ENV_NAMES = {
    CredentialName.PASSWORD: "ZENTAO_PASSWORD",
    CredentialName.API_TOKEN: "ZENTAO_API_TOKEN",
    CredentialName.WEB_COOKIE: "ZENTAO_WEB_COOKIE",
}


class CredentialUnavailableError(RuntimeError):
    """No non-blank credential was available from an allowed source."""


def resolve_environment_reference(value: str, env: Mapping[str, str]) -> SecretStr:
    match = _REFERENCE.fullmatch(value)
    if match is None:
        raise ValueError("secret must be a complete environment reference")
    env_name = match.group(1)
    resolved = env.get(env_name)
    if resolved is None or not resolved.strip():
        raise CredentialUnavailableError(f"environment credential {env_name} is unavailable")
    return SecretStr(resolved)


def resolve_credential(
    name: CredentialName,
    env: Mapping[str, str],
    store: CredentialReader,
    prompt: Callable[[CredentialName], SecretStr | None] | None = None,
) -> SecretStr:
    stored = store.get(name)
    if stored is not None and stored.get_secret_value().strip():
        return stored
    environment_value = env.get(_ENV_NAMES[name])
    if environment_value is not None and environment_value.strip():
        return SecretStr(environment_value)
    prompted = prompt(name) if prompt is not None else None
    if prompted is not None and prompted.get_secret_value().strip():
        return prompted
    raise CredentialUnavailableError(f"credential {name.value} is unavailable")
