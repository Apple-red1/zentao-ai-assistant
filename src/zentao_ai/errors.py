from __future__ import annotations

from enum import StrEnum

from zentao_ai.config import redact


class ErrorCode(StrEnum):
    CONFIG_ERROR = "CONFIG_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_AMBIGUOUS = "USER_AMBIGUOUS"
    BUG_NOT_FOUND = "BUG_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_WRITE_RESULT = "UNKNOWN_WRITE_RESULT"


class ZentaoError(RuntimeError):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
        details: object | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = redact(details) if details is not None else None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "ok": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "retryable": self.retryable,
            },
        }
        if self.details is not None:
            error = result["error"]
            assert isinstance(error, dict)
            error["details"] = self.details
        return result
