from __future__ import annotations


class ZentaoError(RuntimeError):
    """A sanitized provider failure."""


class AuthenticationError(ZentaoError):
    pass


class PermissionDeniedError(ZentaoError):
    pass


class ContractError(ZentaoError):
    pass


class TransportError(ZentaoError):
    pass


class UnknownWriteResultError(TransportError):
    pass
