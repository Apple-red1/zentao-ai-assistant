
from __future__ import annotations

import json
import sys
from typing import Any

from ..internal.errors import ZentaoError
from .presenters.generic import render_human

SENSITIVE_KEYS = {"authorization", "cookie", "setcookie"}


def _sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("_", "").replace("-", "")
    return "password" in normalized or "token" in normalized or normalized in SENSITIVE_KEYS


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("***" if _sensitive_key(key) else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def emit_success(result: object | None, *, json_output: bool) -> None:
    clean = redact(result if result is not None else {"status": "success"})
    if json_output:
        sys.stdout.write(json.dumps(clean, ensure_ascii=False, separators=(",", ":")) + "\n")
    else:
        sys.stdout.write(render_human(clean) + "\n")


def emit_error(exc: ZentaoError, *, json_output: bool) -> None:
    payload = {"error": {"code": exc.code, "message": exc.message, "details": redact(exc.details)}}
    if json_output:
        sys.stderr.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    else:
        sys.stderr.write(f"{exc.code}: {exc.message}\n")
