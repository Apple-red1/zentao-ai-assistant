from __future__ import annotations

from typing import Any, Mapping

SENSITIVE_FRAGMENTS = ("password", "token", "cookie", "secret", "authorization")
REDACTED = "***REDACTED***"


def redact_config(config: Mapping[str, Any]) -> dict[str, Any]:
    def redact(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): REDACTED
                if any(fragment in str(key).lower() for fragment in SENSITIVE_FRAGMENTS)
                else redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    return redact(config)  # type: ignore[no-any-return]
