from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any, Iterable


_SPECIAL_ASSIGNEE_VALUES = frozenset({"closed"})


def dedupe_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    found: dict[str, dict[str, Any]] = {}
    anonymous: list[dict[str, Any]] = []
    duplicates = 0
    for record in records:
        value = record.get("id")
        if value is None:
            anonymous.append(record)
            continue
        key = str(value)
        if key in found:
            duplicates += 1
            continue
        found[key] = record
    def sort_key(item: dict[str, Any]) -> tuple[int, object]:
        value = item.get("id")
        try:
            return (0, int(value))
        except (TypeError, ValueError):
            return (1, str(value))
    return sorted([*found.values(), *anonymous], key=sort_key), duplicates


def first_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return None


def scalar_identity(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("account", "realname", "name", "id"):
            if value.get(key) not in (None, ""):
                return str(value[key])
        return ""
    if isinstance(value, list):
        return ",".join(filter(None, (scalar_identity(item) for item in value)))
    return "" if value is None else str(value)


def assignee(record: dict[str, Any]) -> str:
    value = scalar_identity(first_value(record, "assignedTo", "assigned_to", "assignee", "assignedToAccount", "owner"))
    return "" if value.strip().casefold() in _SPECIAL_ASSIGNEE_VALUES else value


def status(record: dict[str, Any]) -> str:
    return scalar_identity(first_value(record, "status", "stage"))


def priority(record: dict[str, Any]) -> str:
    return scalar_identity(first_value(record, "pri", "priority"))


def severity(record: dict[str, Any]) -> str:
    return scalar_identity(first_value(record, "severity"))


def title(record: dict[str, Any]) -> str:
    return scalar_identity(first_value(record, "title", "name"))


def group_count(records: Iterable[dict[str, Any]], getter, *, empty_label: str | None = None) -> dict[str, int]:
    values = Counter()
    for record in records:
        value = getter(record)
        if value != "":
            values[str(value)] += 1
        elif empty_label is not None:
            values[empty_label] += 1
    return dict(sorted(values.items(), key=lambda item: item[0]))


def is_open(resource: str, record: dict[str, Any]) -> bool:
    current = status(record).lower()
    terminal = {
        "bug": {"closed"},
        "task": {"done", "closed", "cancel", "canceled", "cancelled", "finished"},
        "story": {"closed"},
        "requirement": {"closed"},
        "ticket": {"closed"},
        "feedback": {"closed"},
        "test-task": {"done", "closed", "finished"},
    }.get(resource, {"closed", "done", "finished"})
    return current not in terminal


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text or text.startswith("0000-00-00"):
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def deadline_state(record: dict[str, Any], *, resource: str = "task", today: str | date | None = None) -> str | None:
    deadline = _as_date(first_value(record, "deadline", "end", "endDate"))
    if deadline is None:
        return None
    if isinstance(today, str):
        current = date.fromisoformat(today)
    elif isinstance(today, date):
        current = today
    else:
        current = date.today()
    if not is_open(resource, record):
        return "completed_past_deadline" if deadline < current else "completed"
    if deadline < current:
        return "overdue"
    if (deadline - current).days <= 3:
        return "upcoming"
    return "future"
