from __future__ import annotations

import html
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

from ..errors import ApiError, UsageError
from ..http.legacy import LegacyForm
from .comments import InlineUpload, append_inline_image
from .common import map_enum


_INLINE_IMAGE_SUFFIXES = frozenset({".gif", ".jpeg", ".jpg", ".png", ".webp"})


def validate_inline_images(values: Iterable[str | Path] | None) -> tuple[Path, ...]:
    paths: list[Path] = []
    for value in values or ():
        path = Path(value).expanduser()
        if not path.is_file():
            raise UsageError(f"步骤内嵌图片不是本地文件: {path}")
        if path.suffix.lower() not in _INLINE_IMAGE_SUFFIXES:
            raise UsageError("步骤内嵌图片仅支持 png、jpg、jpeg、gif 或 webp")
        paths.append(path.resolve())
    return tuple(paths)


def positive_id(value: object | None, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise UsageError(f"{field} 必须是正整数")
    return value


def hidden_value(form: LegacyForm, name: str) -> str | None:
    if name == "uid":
        if form.uid_invalid:
            return None
        values = list(form.uid_values)
        # Keep compatibility with callers constructing the legacy two-field
        # form object directly, while treating parsed duplicate controls as an
        # ambiguous page and failing closed.
        if not values:
            values = [value for field_name, value in form.hidden_fields if field_name == name]
        if len(values) != 1:
            return None
        value = values[0].strip()
        return value or None
    for field_name, value in form.hidden_fields:
        if field_name == name and value:
            return value
    return None


def hidden_values(form: LegacyForm, name: str) -> list[str]:
    return [value for field_name, value in form.hidden_fields if field_name == name and value]


def form_values(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        values = value
    elif isinstance(value, str):
        values = value.split(",") if "," in value else [value]
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        values = [value]
    else:
        values = []
    return [str(item).strip() for item in values if str(item).strip()]


def render_steps(steps: object | None, uploads: tuple[InlineUpload, ...]) -> str:
    rendered = html.escape("" if steps is None else str(steps), quote=False)
    for upload in uploads:
        rendered = append_inline_image(rendered, upload.url)
    return rendered


def unique_uploads(uploads: tuple[InlineUpload, ...]) -> tuple[InlineUpload, ...]:
    seen: set[tuple[int, str]] = set()
    result: list[InlineUpload] = []
    for upload in uploads:
        identity = (upload.file_id, upload.url)
        if identity not in seen:
            seen.add(identity)
            result.append(upload)
    return tuple(result)


def contains_inline_reference(steps: str, upload: InlineUpload) -> bool:
    return any(
        marker in steps
        for marker in (
            html.escape(upload.url, quote=True),
            upload.url,
            f"fileID={upload.file_id}",
            f"fileId={upload.file_id}",
        )
    )


def file_entries(detail: dict[str, Any]) -> list[dict[str, Any]]:
    raw = detail.get("files")
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        if any(key in raw for key in ("id", "fileID", "fileId", "objectType", "objectID")):
            return [dict(raw)]
        return [dict(item) for item in raw.values() if isinstance(item, dict)]
    return []


def owns_inline_file(detail: dict[str, Any], bug_id: int, upload: InlineUpload) -> bool:
    for entry in file_entries(detail):
        raw_id = entry.get("id", entry.get("fileID", entry.get("fileId")))
        try:
            file_id = int(raw_id)
            owner_id = int(entry.get("objectID", entry.get("objectId")))
        except (TypeError, ValueError):
            continue
        object_type = str(entry.get("objectType", entry.get("object_type", ""))).lower().replace("-", "")
        if file_id == upload.file_id and owner_id == bug_id and object_type == "bug":
            return True
    return False


def bug_detail(result: object | None, bug_id: int) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ApiError("Bug 详情响应不是对象，无法确认步骤图片", {"object_id": bug_id, "stage": "steps_readback"})
    nested = result.get("bug")
    detail = nested if isinstance(nested, dict) else result
    try:
        actual_id = int(detail.get("id"))
    except (TypeError, ValueError) as exc:
        raise ApiError("Bug 详情缺少有效 ID，无法确认步骤图片", {"object_id": bug_id, "stage": "steps_readback"}) from exc
    if actual_id != bug_id:
        raise ApiError("Bug 详情 ID 与目标不一致，无法确认步骤图片", {"object_id": bug_id, "stage": "steps_readback"})
    return dict(detail)


def extract_bug_id(response: object) -> int | None:
    if not hasattr(response, "url"):
        return None
    value = str(getattr(response, "url", ""))
    query = parse_qs(urlsplit(value).query)
    for key in ("bugID", "bugId", "id"):
        for raw in query.get(key, ()):
            try:
                ident = int(raw)
            except (TypeError, ValueError):
                continue
            if ident > 0:
                return ident
    body = getattr(response, "body", b"")
    text = body.decode("utf-8", errors="ignore") if isinstance(body, bytes) else str(body)
    match = re.search(r"(?:bugID|bugId|bug-id|bug_id)\s*[=:\"']\s*(\d+)", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def create_form_fields(
    *,
    product: object | None,
    title: object | None,
    affected_build: list[object] | None,
    branch: object | None,
    browser: object | None,
    deadline: object | None,
    execution: object | None,
    keywords: object | None,
    module: object | None,
    os: object | None,
    priority: object | None,
    project: object | None,
    severity: object | None,
    steps: str,
    story: object | None,
    task: object | None,
    type: object | None,
    assignee: object | None,
    uid: str,
) -> list[tuple[str, object]]:
    fields: list[tuple[str, object]] = [
        ("uid", uid),
        ("product", map_enum("product", product)),
        ("title", map_enum("title", title)),
        ("steps", steps),
    ]
    for value in affected_build or ():
        fields.append(("openedBuild[]", map_enum("openedBuild", value)))
    for name, value in (
        ("branch", branch),
        ("module", module),
        ("project", project),
        ("execution", execution),
        ("story", story),
        ("task", task),
        ("severity", severity),
        ("pri", priority),
        ("type", type),
        ("os", os),
        ("browser", browser),
        ("assignedTo", assignee),
        ("deadline", deadline),
        ("keywords", keywords),
    ):
        if value is not None:
            fields.append((name, map_enum(name, value)))
    return fields


def edit_form_fields(
    current: dict[str, Any],
    *,
    bug_id: int,
    form: LegacyForm,
    affected_build: list[object] | None,
    execution: object | None,
    priority: object | None,
    project: object | None,
    severity: object | None,
    steps: str,
    story: object | None,
    title: object | None,
    type: object | None,
    uid: str,
) -> list[tuple[str, object]]:
    opened_build = [str(item) for item in (affected_build or ())]
    if not opened_build:
        opened_build = form_values(current.get("openedBuild")) or hidden_values(form, "openedBuild[]")
    if not opened_build:
        raise ApiError(
            "Bug 当前详情和编辑表单均缺少 openedBuild，未执行步骤图片写入",
            {"object_type": "bug", "object_id": bug_id, "stage": "bug_edit_form", "required": ["openedBuild"]},
        )

    fields: list[tuple[str, object]] = [("id", bug_id), ("uid", uid)]
    values: dict[str, object | None] = {
        "title": title if title is not None else current.get("title"),
        "product": current.get("product", current.get("productID")),
        "branch": current.get("branch"),
        "module": current.get("module"),
        "project": project if project is not None else current.get("project", current.get("projectID")),
        "execution": execution if execution is not None else current.get("execution", current.get("executionID")),
        "story": story if story is not None else current.get("story"),
        "task": current.get("task"),
        "severity": severity if severity is not None else current.get("severity"),
        "pri": priority if priority is not None else current.get("pri"),
        "type": type if type is not None else current.get("type"),
        "os": current.get("os"),
        "browser": current.get("browser"),
        "assignedTo": current.get("assignedTo"),
        "deadline": current.get("deadline"),
        "keywords": current.get("keywords"),
        "status": current.get("status"),
    }
    for name, value in values.items():
        if value is None:
            continue
        if name in {"os", "browser"}:
            for item in form_values(value):
                fields.append((f"{name}[]", item))
        else:
            fields.append((name, map_enum(name, value)))
    fields.append(("steps", steps))
    for value in opened_build:
        fields.append(("openedBuild[]", value))
    fields.append(("lastEditedDate", ""))
    return fields
