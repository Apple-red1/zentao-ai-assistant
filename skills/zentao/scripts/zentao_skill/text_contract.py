"""Lossless text-boundary helpers shared by the CLI and high-level skills."""
from __future__ import annotations

import json
from collections.abc import Iterable

from .internal.errors import UsageError


def normalize_multiline_text(value: object | None) -> str | None:
    """Normalize real line endings while leaving ``\\n`` text untouched."""
    if value is None:
        return None
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def decode_json_text(value: str, *, option: str = "--steps-json") -> str:
    """Decode one explicitly JSON-encoded string, never guess at raw text."""
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise UsageError(
            f"{option} 必须是 JSON 字符串",
            {"option": option, "position": exc.pos},
        ) from exc
    if not isinstance(decoded, str):
        raise UsageError(f"{option} 必须编码一个 JSON 字符串", {"option": option})
    return normalize_multiline_text(decoded) or ""


def compose_bug_steps(sections: Iterable[tuple[str, object | None]]) -> str:
    """Join known Bug description sections using real LF characters.

    Empty sections are omitted. Values are normalized only for actual CR/LF
    line endings; a user's literal backslash-n remains ordinary text.
    """
    rendered: list[str] = []
    for label, value in sections:
        text = normalize_multiline_text(value)
        if text is None or not text.strip():
            continue
        rendered.append(f"{label}:\n{text}")
    return "\n\n".join(rendered)


__all__ = ["compose_bug_steps", "decode_json_text", "normalize_multiline_text"]
