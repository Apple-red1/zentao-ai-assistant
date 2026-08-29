from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from ...comment_contract import VERIFIED_COMMENT_RESOURCE_TYPES, is_allowed


_ATTACHMENT_URL_KEYS = ("url", "downloadUrl", "downloadURL", "webPath", "href", "path")
_ATTACHMENT_NAME_KEYS = ("title", "fileName", "filename", "name")
_CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)


class _RichTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(attrs, tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(attrs, tag)

    def _collect(self, attrs: list[tuple[str, str | None]], tag: str) -> None:
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
        self.sources.extend(source for _, source in _CSS_URL_RE.findall(values.get("style", "")) if source)


def _parse_srcset(value: str) -> list[str]:
    return [match.group(1).rstrip(",") for match in re.finditer(r"(data:[^\s]+|[^\s,]+)(?:\s+[^\s,]+)?", value)]


def discover_comment_resources(
    detail: object,
    *,
    object_type: str,
    object_id: int | None,
    add: Any,
    failures: list[dict[str, object]],
) -> None:
    payload = detail
    if isinstance(detail, dict):
        if not isinstance(detail.get("actions"), (list, dict)):
            for key in (object_type, object_type.replace("-", "")):
                value = detail.get(key)
                if isinstance(value, dict):
                    payload = value
                    break
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]
    if not isinstance(payload, dict):
        return
    raw_actions = payload.get("actions")
    if isinstance(raw_actions, dict):
        raw_actions = [raw_actions] if any(key in raw_actions for key in ("id", "actionID", "actionId")) else list(raw_actions.values())
    if not isinstance(raw_actions, list):
        return

    for action in raw_actions:
        if not isinstance(action, dict):
            continue
        if str(action.get("action", action.get("actionType", ""))).strip().lower() != "commented":
            continue
        if _normalize_object_type(action.get("objectType", action.get("object_type"))) != _normalize_object_type(object_type):
            continue
        action_object_id = _positive_id(action.get("objectID", action.get("objectId", action.get("object_id"))))
        if object_id is not None and action_object_id != object_id:
            continue
        action_id = _positive_id(action.get("id", action.get("actionID", action.get("actionId"))))
        if action_id is None:
            failures.append({"origin": "comment", "field": "actions", "code": "COMMENT_RESOURCE_METADATA_INVALID", "message": "评论 action 缺少可追溯的 action_id"})
            continue
        _discover_comment_files(action, action_id=action_id, add=add, failures=failures)
        if is_allowed(object_type, "inline_image"):
            for source in _comment_sources(action):
                add(source, origin="comment", field="actions.comment", action_id=action_id)


def _discover_comment_files(action: dict[str, object], *, action_id: int, add: Any, failures: list[dict[str, object]]) -> None:
    for file_entry in _comment_file_entries(action.get("files")):
        file_object_type = file_entry.get("objectType", file_entry.get("object_type"))
        file_id = _positive_id(file_entry.get("id", file_entry.get("fileID", file_entry.get("fileId"))))
        if file_object_type is not None and _normalize_object_type(file_object_type) != "comment":
            failures.append({"origin": "comment", "field": "actions.files", "action_id": action_id, "file_id": file_id, "code": "COMMENT_RESOURCE_METADATA_INVALID", "message": "评论附件 objectType 不属于 comment action"})
            continue
        owner_id = _positive_id(file_entry.get("objectID", file_entry.get("objectId", file_entry.get("object_id"))))
        if owner_id is not None and owner_id != action_id:
            failures.append({"origin": "comment", "field": "actions.files", "action_id": action_id, "file_id": file_id, "code": "COMMENT_RESOURCE_METADATA_INVALID", "message": "评论附件 objectID 不属于当前 comment action"})
            continue
        source = next((file_entry.get(key) for key in _ATTACHMENT_URL_KEYS if file_entry.get(key)), None)
        name = next((file_entry.get(key) for key in _ATTACHMENT_NAME_KEYS if file_entry.get(key)), None)
        if source is None:
            failures.append({"origin": "comment", "field": "actions.files", "action_id": action_id, "file_id": file_id, "file_name": str(name) if name is not None else None, "code": "RESOURCE_URL_MISSING", "message": "评论附件元数据未提供可下载资源地址"})
        else:
            add(source, origin="comment", file_name=str(name) if name is not None else None, field="actions.files", action_id=action_id, file_id=file_id)


def _comment_sources(action: dict[str, object]) -> list[str]:
    value: object = action.get("comment", action.get("actioncomment", action.get("content", action.get("remark"))))
    if isinstance(value, dict):
        value = value.get("raw", value.get("html", value.get("content", value.get("text"))))
    if not isinstance(value, str) or ("<" not in value and "url(" not in value.lower()):
        return []
    parser = _RichTextParser()
    parser.feed(value)
    return parser.sources + [source for _, source in _CSS_URL_RE.findall(value) if source]


def _comment_file_entries(value: object) -> list[dict[str, object]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    if any(key in value for key in (*_ATTACHMENT_URL_KEYS, *_ATTACHMENT_NAME_KEYS, "id", "fileID", "fileId")):
        return [dict(value)]
    return [dict(item, id=item.get("id", key)) for key, item in value.items() if isinstance(item, dict)]


def _positive_id(value: object) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _normalize_object_type(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "").replace("_", "")


def _looks_like_file_link(source: str) -> bool:
    from pathlib import Path
    from urllib.parse import urlsplit

    parsed = urlsplit(source)
    suffix = Path(parsed.path.lower()).suffix
    if suffix and suffix not in {".html", ".htm", ".php", ".asp", ".aspx", ".jsp"}:
        return True
    hint = f"{parsed.path}?{parsed.query}".lower()
    return any(token in hint for token in ("/file-", "/files/", "/file/", "download", "fileid", "file-id"))
