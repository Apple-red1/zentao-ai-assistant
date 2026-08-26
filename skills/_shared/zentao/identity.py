"""Safe, deterministic identity resolution for higher-level ZenTao skills."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, NoReturn


Record = Mapping[str, Any]


class AmbiguousMatchError(ValueError):
    """Raised when a requested identity has more than one exact match."""

    kind: str
    value: str
    candidates: list[str]

    def __init__(self, kind: str, value: Any, candidates: Iterable[str]) -> None:
        self.kind = kind
        self.value = value
        self.candidates = [str(candidate) for candidate in candidates]
        super().__init__(f"{kind} {value!r} matches multiple candidates")


class MatchNotFoundError(ValueError):
    """Raised when a requested identity has no exact match."""

    kind: str
    value: str

    def __init__(self, kind: str, value: Any) -> None:
        self.kind = kind
        self.value = value
        super().__init__(f"{kind} {value!r} was not found")


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)


def _text_equals(actual: Any, expected: Any) -> bool:
    actual_text = _as_text(actual)
    expected_text = _as_text(expected)
    return actual_text not in (None, "") and actual_text == expected_text


def _text_case_insensitive_equals(actual: Any, expected: Any) -> bool:
    actual_text = _as_text(actual)
    expected_text = _as_text(expected)
    return actual_text not in (None, "") and expected_text is not None and actual_text.lower() == expected_text.lower()


def _matches_any(record: Record, value: Any, fields: tuple[str, ...]) -> bool:
    return any(_text_equals(record.get(field), value) for field in fields)


def _candidate_identifier(record: Record, *, user: bool) -> str:
    """Return only a stable identifier for ambiguity metadata."""
    keys = ("account", "id") if user else ("id",)
    for key in keys:
        value = record.get(key)
        if isinstance(value, (str, int, float, bool)) and value not in (None, ""):
            return str(value)
    return ""


def _ambiguous(kind: str, value: Any, matches: list[Record], *, user: bool) -> NoReturn:
    raise AmbiguousMatchError(kind, value, (_candidate_identifier(record, user=user) for record in matches))


def _resolve_stage(kind: str, value: Any, matches: list[Record], *, user: bool) -> Record | None:
    if len(matches) > 1:
        _ambiguous(kind, value, matches, user=user)
    return matches[0] if matches else None


def resolve_user(records: Iterable[Record], value: Any) -> Record:
    """Resolve one user without guessing between equally valid identities.

    Matching is deliberately staged: case-sensitive account, exact realname or
    name, then case-insensitive account.  A non-unique match at any stage is an
    error and never falls through to a weaker matching stage.
    """
    rows = list(records)

    exact_account = [record for record in rows if _text_equals(record.get("account"), value)]
    resolved = _resolve_stage("user", value, exact_account, user=True)
    if resolved is not None:
        return resolved

    exact_name = [record for record in rows if _matches_any(record, value, ("realname", "name"))]
    resolved = _resolve_stage("user", value, exact_name, user=True)
    if resolved is not None:
        return resolved

    folded_account = [record for record in rows if _text_case_insensitive_equals(record.get("account"), value)]
    resolved = _resolve_stage("user", value, folded_account, user=True)
    if resolved is not None:
        return resolved

    raise MatchNotFoundError("user", value)


def _positive_integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if not isinstance(value, str) or not value or any(char < "0" or char > "9" for char in value):
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _id_equals(record_id: Any, expected: int) -> bool:
    actual = _positive_integer(record_id)
    return actual == expected


def resolve_named_entity(records: Iterable[Record], value: Any, *, kind: str) -> Record:
    """Resolve an entity by positive numeric ID or exact name/title.

    A positive integer value selects the ID stage exclusively.  Zero, negative
    integers, and non-numeric values are treated as ordinary exact name/title
    queries; no whitespace normalization or fuzzy matching is performed.
    """
    rows = list(records)
    numeric_id = _positive_integer(value)
    if numeric_id is not None:
        exact_id = [record for record in rows if _id_equals(record.get("id"), numeric_id)]
        resolved = _resolve_stage(kind, value, exact_id, user=False)
        if resolved is not None:
            return resolved
        raise MatchNotFoundError(kind, value)

    exact_name = [record for record in rows if _matches_any(record, value, ("name", "title"))]
    resolved = _resolve_stage(kind, value, exact_name, user=False)
    if resolved is not None:
        return resolved
    raise MatchNotFoundError(kind, value)


__all__ = [
    "AmbiguousMatchError",
    "MatchNotFoundError",
    "resolve_named_entity",
    "resolve_user",
]
