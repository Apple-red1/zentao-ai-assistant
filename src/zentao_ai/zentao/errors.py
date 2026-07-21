from __future__ import annotations

from typing import Final


McpErrorPayload = dict[str, str]


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


class IdentityNotFoundError(ContractError):
    pass


class AmbiguousIdentityError(ContractError):
    pass


class TransportError(ZentaoError):
    pass


class UnknownWriteResultError(TransportError):
    pass


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
            "code": "AMBIGUOUS_IDENTITY",
            "type": "ambiguous_identity",
            "message": "Requested identity is ambiguous.",
        }
    if isinstance(error, PermissionDeniedError):
        return {
            "code": "PERMISSION_DENIED",
            "type": "permission_denied",
            "message": "Permission was denied.",
        }
    if isinstance(error, ContractError):
        return {
            "code": "INVALID_ENVELOPE",
            "type": "invalid_envelope",
            "message": "Received an invalid Zentao response.",
        }
    return _INTERNAL_ERROR.copy()
