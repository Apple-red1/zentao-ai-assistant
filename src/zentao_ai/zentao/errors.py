from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final


McpErrorPayload = dict[str, Any]


_INTERNAL_ERROR: Final[McpErrorPayload] = {
    "code": "INTERNAL_ERROR",
    "type": "internal_error",
    "message": "An internal error occurred.",
}


class ZentaoError(RuntimeError):
    """A sanitized provider failure."""


class AuthenticationError(ZentaoError):
    pass


class PermissionDeniedError(ZentaoError):
    pass


class ContractError(ZentaoError):
    pass


class InvalidBugContractError(ContractError):
    pass


class MissingStableVersionError(ContractError):
    pass


class IdentityNotFoundError(ContractError):
    pass


class AmbiguousIdentityError(ContractError):
    def __init__(
        self,
        message: str,
        *,
        candidates: tuple[Mapping[str, object], ...] = (),
    ) -> None:
        super().__init__(message)
        self.candidates = tuple(
            candidate
            for value in candidates
            if (candidate := _sanitized_identity_candidate(value)) is not None
        )


class TransportError(ZentaoError):
    pass


class UnknownWriteResultError(TransportError):
    pass


def _sanitized_identity_candidate(
    value: Mapping[str, object],
) -> dict[str, str | None] | None:
    account = value.get("account")
    display_name = value.get("displayName")
    if not isinstance(account, str) or not account.strip():
        return None
    return {
        "account": account.strip(),
        "displayName": display_name.strip()
        if isinstance(display_name, str) and display_name.strip()
        else None,
    }


def sanitized_mcp_error(error: Exception) -> McpErrorPayload:
    """Return the stable, public error details safe for MCP clients."""
    if isinstance(error, IdentityNotFoundError):
        return {
            "code": "IDENTITY_NOT_FOUND",
            "type": "identity_not_found",
            "message": "Requested identity was not found.",
        }
    if isinstance(error, AmbiguousIdentityError):
        return {
            "code": "IDENTITY_AMBIGUOUS",
            "type": "identity_ambiguous",
            "message": "Requested identity is ambiguous.",
            "details": {"candidates": list(error.candidates)},
        }
    if isinstance(error, AuthenticationError):
        return {
            "code": "AUTHENTICATION_FAILED",
            "type": "authentication_failed",
            "message": "Authentication failed.",
        }
    if isinstance(error, PermissionDeniedError):
        return {
            "code": "PERMISSION_DENIED",
            "type": "permission_denied",
            "message": "Permission was denied.",
        }
    if isinstance(error, MissingStableVersionError):
        return {
            "code": "MISSING_STABLE_VERSION",
            "type": "missing_stable_version",
            "message": "Bug response is missing a stable version.",
        }
    if isinstance(error, InvalidBugContractError):
        return {
            "code": "INVALID_BUG_CONTRACT",
            "type": "invalid_bug_contract",
            "message": "Received an invalid Bug contract.",
        }
    if isinstance(error, ContractError):
        return {
            "code": "INVALID_RESPONSE_ENVELOPE",
            "type": "invalid_response_envelope",
            "message": "Received an invalid Zentao response.",
        }
    return _INTERNAL_ERROR.copy()
