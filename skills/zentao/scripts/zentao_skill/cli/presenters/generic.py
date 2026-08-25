
from __future__ import annotations

import json
from typing import Any


def render_human(value: Any) -> str:
    if isinstance(value, dict):
        for key, items in value.items():
            if isinstance(items, list) and items and all(isinstance(item, dict) for item in items):
                return _table(items)
        return "\n".join(f"{key}: {_scalar(item)}" for key, item in value.items())
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return _table(value)
    return _scalar(value)


def _scalar(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(empty)"
    preferred = ["id", "name", "title", "status", "severity"]
    columns = [c for c in preferred if any(c in row for row in rows)]
    if not columns:
        columns = list(rows[0])[:6]
    widths = {c: max(len(c), *(len(_scalar(row.get(c, ""))) for row in rows)) for c in columns}
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    divider = "  ".join("-" * widths[c] for c in columns)
    body = ["  ".join(_scalar(row.get(c, "")).ljust(widths[c]) for c in columns) for row in rows]
    return "\n".join([header, divider, *body])
