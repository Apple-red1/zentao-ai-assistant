from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_HTML_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_HTML_SUFFIXES = frozenset({".html", ".htm"})
_HTML_ERROR_MARKERS = (
    "fatal error", "parse error", "uncaught exception", "stack trace",
    "login", "sign in", "登录", "请登录",
)


def resource_content_failure(item: dict[str, Any], source: Path) -> dict[str, Any] | None:
    size = source.stat().st_size
    content_type = str(item.get("content_type") or "").split(";", 1)[0].strip().lower()
    if size == 0:
        return {"code": "RESOURCE_CONTENT_INVALID", "message": "资源文件内容为空", "details": {"content_type": content_type, "size": size}}
    with source.open("rb") as stream:
        sample = stream.read(8192)
    text = sample.decode("utf-8", errors="ignore").lstrip("\ufeff \t\r\n").lower()
    looks_like_html = bool(re.search(r"<!doctype\s+html\b|<html(?:\s|>)|<(?:head|body|form|br|div|p)(?:\s|>)", text))
    explicit_html = Path(str(item.get("file_name") or "")).suffix.lower() in _HTML_SUFFIXES
    if (content_type in _HTML_CONTENT_TYPES or looks_like_html) and (not explicit_html or any(marker in text for marker in _HTML_ERROR_MARKERS)):
        return {"code": "RESOURCE_CONTENT_INVALID", "message": "资源文件疑似 HTML 登录页或错误页", "details": {"content_type": content_type, "size": size}}
    return None
