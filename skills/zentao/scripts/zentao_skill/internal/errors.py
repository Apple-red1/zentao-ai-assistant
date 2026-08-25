
from __future__ import annotations

from typing import Any


class ZentaoError(Exception):
    exit_code = 1

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class UsageError(ZentaoError):
    exit_code = 2

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("USAGE_ERROR", message, details)


class ConfigError(ZentaoError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("CONFIG_ERROR", message, details)


class ApiError(ZentaoError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("API_ERROR", message, details)


class NetworkError(ZentaoError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("NETWORK_ERROR", message, details)


class UnknownWriteResult(ZentaoError):
    def __init__(self, message: str = "写请求可能已被服务器执行，但客户端无法确认最终结果") -> None:
        super().__init__("UNKNOWN_WRITE_RESULT", message, {})


class MalformedResponse(ZentaoError):
    def __init__(self, message: str = "ZenTao 返回了无法解析的 JSON") -> None:
        super().__init__("MALFORMED_RESPONSE", message, {})


class TransportFailure(Exception):
    def __init__(self, message: str, *, definitely_not_sent: bool) -> None:
        super().__init__(message)
        self.message = message
        self.definitely_not_sent = definitely_not_sent


class HttpFailure(Exception):
    def __init__(self, status: int, body: object | None) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body
