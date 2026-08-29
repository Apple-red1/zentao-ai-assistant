from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from ..errors import ApiError
from .comment_models import CRITICAL_FIELDS, CommentSnapshot


class _HiddenFieldParser(HTMLParser):
    def __init__(self, name: str) -> None:
        super().__init__(convert_charrefs=True)
        self.name = name
        self.value: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return
        values = {key.lower(): value for key, value in attrs}
        if values.get("name") != self.name:
            return
        input_type = (values.get("type") or "").lower()
        classes = set((values.get("class") or "").lower().split())
        if input_type not in {"", "hidden"} and "hidden" not in classes:
            return
        value = values.get("value")
        if value:
            self.value = value


def extract_hidden_field(body: bytes, name: str) -> str | None:
    parser = _HiddenFieldParser(name)
    try:
        parser.feed(body.decode("utf-8", errors="replace"))
        parser.close()
    except Exception:
        return None
    return parser.value


@dataclass
class _PageAction:
    value: dict[str, Any]
    start_depth: int
    text: list[str]
    image_sources: list[str]


class _DetailPageParser(HTMLParser):
    def __init__(self, *, object_type: str) -> None:
        super().__init__(convert_charrefs=True)
        self.object_type = object_type
        self.actions: list[dict[str, Any]] = []
        self.critical_fields: dict[str, Any] = {}
        self._depth = 0
        self._frames: list[_PageAction] = []
        self._script_depth: int | None = None
        self._script_text: list[str] = []
        self.json_actions: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs if value is not None}
        normalized = tag.lower()
        if normalized == "script":
            self._script_depth = self._depth
            self._script_text = []

        self._collect_critical(values)
        self._collect_file_attributes(values)
        history_panel = values.get("zui-create-historypanel")
        if history_panel:
            self._parse_history_panel(history_panel)
        marker = _page_action_marker(values)
        if marker is not None:
            self._frames.append(_PageAction(marker, self._depth, [], []))
        if self._frames and normalized == "img" and values.get("src"):
            self._frames[-1].image_sources.append(values["src"])
        self._depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._script_depth is not None:
            self._script_text.append(data)
        if self._frames and data.strip():
            self._frames[-1].text.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if self._depth > 0:
            self._depth -= 1
        if normalized == "script" and self._script_depth is not None:
            self._parse_script("".join(self._script_text))
            self._script_depth = None
            self._script_text = []
        while self._frames and self._frames[-1].start_depth == self._depth:
            frame = self._frames.pop()
            value = frame.value
            if not value.get("comment"):
                text = " ".join(part.strip() for part in frame.text if part.strip())
                if text:
                    value["comment"] = text
            if frame.image_sources:
                comment = str(value.get("comment") or "")
                for source in frame.image_sources:
                    if source not in comment:
                        comment += f'<img src="{source}">'
                value["comment"] = comment
            self.actions.append(value)

    def _collect_critical(self, values: dict[str, str]) -> None:
        fields = set().union(*CRITICAL_FIELDS.values())
        for field in fields:
            value = values.get(f"data-{field}")
            if value is not None and field not in self.critical_fields:
                self.critical_fields[field] = value
        field = values.get("data-field")
        value = values.get("data-value", values.get("value"))
        if field and value is not None and field in {"status", "title", "name", "product", "project", "execution", "model"}:
            self.critical_fields.setdefault(field, value)

    def _collect_file_attributes(self, values: dict[str, str]) -> None:
        if not self._frames:
            return
        raw_id = values.get("data-file-id", values.get("data-fileid"))
        if raw_id is None:
            return
        files = self._frames[-1].value.setdefault("files", [])
        if not isinstance(files, list):
            return
        entry: dict[str, Any] = {"id": raw_id}
        for source, target in (
            ("data-object-type", "objectType"),
            ("data-object-id", "objectID"),
            ("data-name", "name"),
            ("data-file-name", "name"),
            ("data-size", "size"),
        ):
            if values.get(source) is not None:
                entry[target] = values[source]
        files.append(entry)

    def _parse_script(self, value: str) -> None:
        stripped = value.strip()
        if not stripped:
            return
        try:
            payload = json.loads(stripped)
        except (TypeError, ValueError):
            return
        if isinstance(payload, dict) and isinstance(payload.get("actions"), list):
            self.json_actions.extend(item for item in payload["actions"] if isinstance(item, dict))

    def _parse_history_panel(self, value: str) -> None:
        decoded = html.unescape(value)
        match = re.search(r"[\"']actions[\"']\s*:\s*", decoded)
        if match is None:
            return
        start = decoded.find("[", match.end())
        if start < 0:
            return
        try:
            raw_actions, _ = json.JSONDecoder().raw_decode(decoded[start:])
        except (TypeError, ValueError):
            return
        if not isinstance(raw_actions, list):
            return
        object_id_match = re.search(r"[\"']objectID[\"']\s*:\s*([1-9][0-9]*)", decoded)
        object_id = int(object_id_match.group(1)) if object_id_match else None
        for raw_action in raw_actions:
            if not isinstance(raw_action, dict):
                continue
            action = dict(raw_action)
            action.setdefault("objectType", self.object_type)
            if object_id is not None:
                action.setdefault("objectID", object_id)
            _normalize_page_action(action)
            self.json_actions.append(action)


def _page_action_marker(values: dict[str, str]) -> dict[str, Any] | None:
    raw_id = values.get("data-action-id", values.get("data-actionid"))
    if raw_id is None:
        element_id = values.get("id", "")
        match = re.search(r"(?:action|history)[_-]?([1-9][0-9]*)", element_id, re.IGNORECASE)
        classes = set((values.get("class", "")).lower().split())
        if match and ("action" in classes or "history" in classes or "history-item" in classes):
            raw_id = match.group(1)
        elif "data-id" in values and ("action" in classes or "history" in classes or "history-item" in classes):
            raw_id = values["data-id"]
    if raw_id is None or not re.fullmatch(r"[1-9][0-9]*", raw_id.strip()):
        return None
    value: dict[str, Any] = {"id": int(raw_id)}
    for source, target in (
        ("data-action", "action"),
        ("data-type", "action"),
        ("data-object-type", "objectType"),
        ("data-object-id", "objectID"),
        ("data-comment", "comment"),
        ("data-actioncomment", "comment"),
        ("data-account", "actor"),
    ):
        if values.get(source) is not None:
            value[target] = values[source]
    return value


def _normalize_page_action(action: dict[str, Any]) -> None:
    raw_files = action.get("files")
    if isinstance(raw_files, list):
        file_names = _history_file_names(action)
        normalized: list[dict[str, Any]] = []
        for index, raw_file in enumerate(raw_files):
            if not isinstance(raw_file, dict):
                continue
            entry = dict(raw_file)
            file_id = _positive_id(entry.get("id", entry.get("fileID", entry.get("fileId"))))
            if file_id is not None:
                entry.setdefault("id", file_id)
                entry.setdefault("objectType", "comment")
                action_id = _positive_id(action.get("id"))
                if action_id is not None:
                    entry.setdefault("objectID", action_id)
                entry.setdefault("url", f"/index.php?m=file&f=download&fileID={file_id}")
            if not any(entry.get(key) for key in ("title", "name", "fileName", "filename")):
                if index < len(file_names):
                    entry["name"] = file_names[index]
                else:
                    pathname = entry.get("pathname")
                    extension = str(entry.get("extension") or "").strip().lstrip(".")
                    if pathname:
                        name = Path(str(pathname)).name
                        if extension and not Path(name).suffix:
                            name = f"{name}.{extension}"
                        entry["name"] = name
            normalized.append(entry)
        action["files"] = normalized
    if not action.get("actor"):
        content = html.unescape(str(action.get("content") or ""))
        actor_match = re.search(r"由\s*<strong[^>]*>([^<]+)</strong>", content, re.IGNORECASE)
        if actor_match:
            action["actor"] = actor_match.group(1).strip()


def _history_file_names(action: dict[str, Any]) -> list[str]:
    history = html.unescape(str(action.get("historyChanges") or ""))
    if not history:
        return []
    return [match.strip() for match in re.findall(r'["“]([^"”]+)["”]', history) if match.strip()]


def _positive_id(value: object) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def parse_page_snapshot(body: bytes, *, object_type: str) -> CommentSnapshot:
    parser = _DetailPageParser(object_type=object_type)
    try:
        parser.feed(body.decode("utf-8", errors="replace"))
        parser.close()
    except Exception as exc:
        raise ApiError(
            "ZenTao 对象详情页无法解析，无法进行评论回读",
            {"object_type": object_type, "stage": "readback"},
        ) from exc
    actions = parser.json_actions or parser.actions
    return CommentSnapshot(tuple(actions), parser.critical_fields)
