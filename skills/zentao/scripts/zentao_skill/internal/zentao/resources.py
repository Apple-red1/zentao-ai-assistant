from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, unquote_to_bytes, urlencode, urlsplit, urlunsplit

from ..errors import ApiError, UsageError
from .session import ZentaoSession


OBJECT_VIEW_PATHS = {
    "bug": "/bugs/{id}",
    "epic": "/epics/{id}",
    "execution": "/executions/{id}",
    "feedback": "/feedbacks/{id}",
    "product": "/products/{id}",
    "product-plan": "/productplans/{id}",
    "program": "/programs/{id}",
    "requirement": "/requirements/{id}",
    "story": "/stories/{id}",
    "task": "/tasks/{id}",
    "test-case": "/testcases/{id}",
    "ticket": "/tickets/{id}",
    "user": "/users/{id}",
}
RESOURCE_OBJECT_TYPES = frozenset(OBJECT_VIEW_PATHS)

_ATTACHMENT_URL_KEYS = ("url", "downloadUrl", "downloadURL", "webPath", "href", "path")
_ATTACHMENT_NAME_KEYS = ("title", "fileName", "filename", "name")
_CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
_PAGE_SUFFIXES = {".html", ".htm", ".php", ".asp", ".aspx", ".jsp"}


@dataclass(frozen=True)
class ResourceCandidate:
    source: str
    origin: str
    file_name: str | None = None
    field: str | None = None


class _RichTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(tag, attrs)

    def _collect(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value for name, value in attrs if value is not None}
        tag = tag.lower()
        if tag in {"img", "audio", "video", "source", "track", "embed"} and values.get("src"):
            self.sources.append(values["src"])
        if tag in {"img", "source"} and values.get("srcset"):
            self.sources.extend(_parse_srcset(values["srcset"]))
        if tag == "video" and values.get("poster"):
            self.sources.append(values["poster"])
        if tag == "object" and values.get("data"):
            self.sources.append(values["data"])
        if tag == "a" and values.get("href") and ("download" in values or _looks_like_file_link(values["href"])):
            self.sources.append(values["href"])
        style = values.get("style", "")
        for _, source in _CSS_URL_RE.findall(style):
            if source:
                self.sources.append(source)


def _parse_srcset(value: str) -> list[str]:
    sources: list[str] = []
    for match in re.finditer(r"(data:[^\s]+|[^\s,]+)(?:\s+[^\s,]+)?", value):
        source = match.group(1).rstrip(",")
        if source:
            sources.append(source)
    return sources


def discover_resources(detail: object) -> tuple[list[ResourceCandidate], list[dict[str, object]]]:
    candidates: list[ResourceCandidate] = []
    failures: list[dict[str, object]] = []
    seen: set[str] = set()

    def add(source: object, *, origin: str, file_name: str | None = None, field: str | None = None) -> None:
        if not isinstance(source, str) or not source.strip():
            return
        normalized = source.strip()
        if normalized in seen:
            return
        seen.add(normalized)
        candidates.append(ResourceCandidate(normalized, origin, file_name=file_name, field=field))

    def attachment_entries(value: object) -> list[object]:
        if isinstance(value, list):
            return list(value)
        if isinstance(value, dict):
            if any(key in value for key in (*_ATTACHMENT_URL_KEYS, *_ATTACHMENT_NAME_KEYS)):
                return [value]
            return list(value.values())
        return [value]

    def walk_attachments(value: object, path: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                if str(key).lower() == "files":
                    for entry in attachment_entries(item):
                        if isinstance(entry, str):
                            add(entry, origin="attachment", field=item_path)
                            continue
                        if not isinstance(entry, dict):
                            continue
                        source = next((entry.get(key) for key in _ATTACHMENT_URL_KEYS if entry.get(key)), None)
                        name = next((entry.get(key) for key in _ATTACHMENT_NAME_KEYS if entry.get(key)), None)
                        if source is None:
                            failures.append({
                                "origin": "attachment",
                                "field": item_path,
                                "file_name": str(name) if name is not None else None,
                                "code": "RESOURCE_URL_MISSING",
                                "message": "附件元数据未提供可下载资源地址",
                            })
                        else:
                            add(source, origin="attachment", file_name=str(name) if name is not None else None, field=item_path)
                    continue
                walk_attachments(item, item_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk_attachments(item, f"{path}[{index}]")

    def walk_rich_text(value: object, path: str = "", *, inside_files: bool = False) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                walk_rich_text(item, item_path, inside_files=inside_files or str(key).lower() == "files")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk_rich_text(item, f"{path}[{index}]", inside_files=inside_files)
        elif isinstance(value, str) and not inside_files and ("<" in value or "url(" in value.lower()):
            parser = _RichTextParser()
            parser.feed(value)
            for source in parser.sources:
                add(source, origin="rich_text", field=path)
            for _, source in _CSS_URL_RE.findall(value):
                if source:
                    add(source, origin="rich_text", field=path)

    walk_attachments(detail)
    walk_rich_text(detail)
    return candidates, failures


def display_source(source: str) -> str:
    if source.startswith("data:"):
        metadata = source[5:].split(",", 1)[0]
        return f"data:{metadata},..."
    try:
        parsed = urlsplit(source)
        # Accessing ``port`` validates malformed ports; keep the user-facing
        # failure path safe even when the source is not a valid URL.
        port = parsed.port
    except ValueError:
        return "[invalid resource URL]"
    if not parsed.query:
        query = ""
    else:
        pairs = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            normalized = key.lower().replace("_", "").replace("-", "")
            sensitive = any(token in normalized for token in ("password", "token", "authorization", "cookie", "signature", "secret"))
            pairs.append((key, "***" if sensitive else value))
        query = urlencode(pairs, doseq=True)
    netloc = parsed.netloc
    if parsed.username is not None or parsed.password is not None:
        host = parsed.hostname or ""
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        netloc = f"***@{host}"
        if port is not None:
            netloc += f":{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, query, ""))


def source_file_name(source: str) -> str | None:
    if source.startswith("data:"):
        return None
    name = Path(urlsplit(source).path).name
    return unquote(name) if name else None


def decode_data_uri(source: str) -> tuple[bytes, str]:
    if not source.startswith("data:") or "," not in source:
        raise ValueError("不是有效的 data URI")
    metadata, payload = source[5:].split(",", 1)
    parts = metadata.split(";") if metadata else []
    content_type = parts[0] if parts and "/" in parts[0] else "text/plain"
    try:
        if any(part.lower() == "base64" for part in parts[1:]):
            return base64.b64decode(payload, validate=True), content_type
        return unquote_to_bytes(payload), content_type
    except (binascii.Error, ValueError) as exc:
        raise ValueError("data URI 内容无法解码") from exc


def _looks_like_file_link(source: str) -> bool:
    if source.startswith("data:"):
        return True
    parsed = urlsplit(source)
    path = parsed.path.lower()
    suffix = Path(path).suffix.lower()
    if suffix and suffix not in _PAGE_SUFFIXES:
        return True
    hint = f"{path}?{parsed.query}".lower()
    return any(token in hint for token in ("/file-", "/files/", "/file/", "download", "fileid", "file-id"))


class ResourcesAPI:
    OBJECT_TYPES = RESOURCE_OBJECT_TYPES

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    def view_object(self, *, object_type: str, item_id: int) -> dict[str, Any]:
        template = OBJECT_VIEW_PATHS.get(object_type)
        if template is None:
            raise UsageError("--object-type 不是当前资源获取能力支持的对象类型")
        result = self.session.get(template.format(id=item_id))
        if not isinstance(result, dict):
            raise ApiError("ZenTao 对象详情响应不是可解析对象", {"object_type": object_type, "object_id": item_id})
        return result

    def download(self, *, source: str, destination: str | Path) -> dict[str, object]:
        return self.session.download_resource(source, destination)
