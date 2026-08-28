from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CRITICAL_FIELDS = {
    "bug": ("status", "title", "product", "project", "execution", "severity", "pri", "type"),
    "story": ("status", "title", "product", "project", "execution", "priority"),
    "product": ("status", "name", "title"),
    "task": ("status", "name", "title", "execution", "project"),
    "execution": ("status", "name", "title", "project", "product"),
    "project": ("status", "name", "title", "model"),
    "test-task": ("status", "name", "title", "product", "execution"),
    "product-plan": ("status", "name", "title", "product"),
    "release": ("status", "name", "title", "product"),
    "build": ("status", "name", "title", "product", "project", "execution"),
}


@dataclass(frozen=True)
class CommentSnapshot:
    actions: tuple[dict[str, Any], ...]
    critical_fields: dict[str, Any]
