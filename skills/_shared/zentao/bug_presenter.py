"""Shared deterministic Markdown rendering for personal Bug lists."""
from __future__ import annotations

import html
from collections.abc import Iterable, Mapping
from typing import Any


PLACEHOLDER = "—"
HEADERS = (
    "Bug ID", "标题", "状态", "优先级", "严重程度", "当前指派", "解决人", "创建时间", "解决时间",
)


def _value(item: Mapping[str, Any], *keys: str) -> object | None:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def _display(value: object | None) -> str:
    if value in (None, ""):
        return PLACEHOLDER
    if isinstance(value, Mapping):
        for key in ("realname", "account", "name", "id"):
            nested = value.get(key)
            if nested not in (None, ""):
                return str(nested)
        return PLACEHOLDER
    if isinstance(value, (list, tuple)):
        values = [_display(item) for item in value]
        return ", ".join(item for item in values if item != PLACEHOLDER) or PLACEHOLDER
    return str(value)


def _level(value: object | None, prefix: str) -> str:
    text = _display(value)
    if text == PLACEHOLDER:
        return text
    if text in {"1", "2", "3", "4"}:
        return f"{prefix}{text}"
    return text


def _status(value: object | None) -> str:
    text = _display(value)
    return {
        "active": "激活",
        "resolved": "已解决",
        "closed": "已关闭",
        "doing": "进行中",
        "done": "已完成",
    }.get(text.casefold(), text)


def _cell(value: object | None) -> str:
    text = html.escape(_display(value), quote=False)
    text = text.replace("\\", "\\\\")
    for char in ("|", "[", "]", "*", "_", "`", "#"):
        text = text.replace(char, "\\" + char)
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _id_key(value: object) -> int | str:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    return str(value)


def render_bug_table(
    items: Iterable[Mapping[str, Any]],
    *,
    urls: Mapping[int | str, str] | None = None,
    heading: str = "## 我的 Bug",
    empty_message: str = "没有 Bug。",
    complete: bool = True,
    partial_failures: Iterable[object] = (),
) -> str:
    """Render one stable table row per Bug and append completeness details."""
    rows = list(items)
    url_map = urls or {}
    failures = list(partial_failures)
    link_failures: list[str] = []
    lines = [heading, "", f"查询到 {len(rows)} 条 Bug。", ""]
    lines.append("| " + " | ".join(HEADERS) + " |")
    lines.append("| " + " | ".join("---" for _ in HEADERS) + " |")
    for item in rows:
        raw_id = _value(item, "id", "bug_id")
        key = _id_key(raw_id)
        link = url_map.get(key)
        if link is None and isinstance(key, int):
            link = url_map.get(str(key))
        if isinstance(link, str) and link:
            bug_cell = f"[{key}]({link})"
        else:
            bug_cell = f"{_cell(key)}（链接生成失败）"
            link_failures.append(f"Bug {key} 链接生成失败；未猜测 URL")
        values = (
            bug_cell,
            _cell(_value(item, "title", "name")),
            _cell(_status(_value(item, "status", "stage"))),
            _cell(_level(_value(item, "priority", "pri"), "P")),
            _cell(_level(_value(item, "severity"), "S")),
            _cell(_value(item, "assignee", "assignedTo", "assigned_to", "assignedToAccount")),
            _cell(_value(item, "resolved_by", "resolvedBy", "resolvedByAccount")),
            _cell(_value(item, "opened_date", "openedDate", "created_date", "createdDate")),
            _cell(_value(item, "resolved_date", "resolvedDate")),
        )
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(["", empty_message if not rows else ""])
    if not complete or failures:
        lines.extend(["", "## 数据完整性", ""])
        if not complete:
            lines.append("查询不完整，以上仅为已成功读取的 Bug，不能视为全部结果。")
        for failure in failures:
            if isinstance(failure, Mapping):
                code = failure.get("code", "READ_FAILED")
                details = " / ".join(
                    str(failure[key]) for key in ("resource", "scope", "bug_id", "field", "page")
                    if key in failure
                )
                lines.append(f"- `{code}`" + (f"：{_cell(details)}" if details else ""))
            else:
                lines.append(f"- {_cell(failure)}")
    if link_failures:
        lines.extend(["", "## 链接生成", ""])
        lines.extend(f"- {_cell(message)}" for message in dict.fromkeys(link_failures))
    return "\n".join(lines).rstrip()


__all__ = ["HEADERS", "PLACEHOLDER", "render_bug_table"]
