"""Lightweight validation helpers for report payloads."""

from __future__ import annotations

from typing import Any


class ReportError(ValueError):
    """Raised when a report payload violates the v2 contract."""


def require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReportError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReportError(f"{field} must be an array")
    return value


def text(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ReportError(f"{field} must be nonempty")
    return result


def optional_text(value: Any) -> str | None:
    result = str(value or "").strip()
    return result or None


def integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReportError(f"{field} must be a nonnegative integer")
    return value
