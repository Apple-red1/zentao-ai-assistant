from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, urljoin, urlsplit

from ...comment_contract import is_allowed
from ..errors import ApiError
from ..http.legacy import LegacyPageResponse, LegacyWebClient
from .comment_models import CRITICAL_FIELDS, CommentSnapshot
from .comment_pages import extract_hidden_field, parse_page_snapshot
from .session import ZentaoSession


_API_DETAIL_PATHS = {
    "bug": "/bugs/{id}",
    "story": "/stories/{id}",
    "product": "/products/{id}",
    "task": "/tasks/{id}",
    "execution": "/executions/{id}",
    "product-plan": "/productplans/{id}",
}


@dataclass(frozen=True)
class InlineUpload:
    file_id: int
    url: str


class CommentAPI:
    """Adapter for the fixed page protocol and object-specific readback."""

    def __init__(
        self,
        session: ZentaoSession,
        *,
        web_client_factory: Callable[..., LegacyWebClient] = LegacyWebClient,
    ) -> None:
        self.session = session
        self.web_client_factory = web_client_factory
        self._web_client: LegacyWebClient | None = None

    def get_comment_form(self, *, object_type: str, object_id: int) -> str:
        response = self._web().get_comment_form(object_type=object_type, object_id=object_id)
        uid = extract_hidden_field(response.body, "uid")
        if not uid:
            raise ApiError(
                "ZenTao 评论表单缺少 uid，未执行评论写入",
                {"object_type": object_type, "object_id": object_id, "stage": "comment_form"},
            )
        return uid

    def post_comment(
        self,
        *,
        object_type: str,
        object_id: int,
        uid: str,
        actioncomment: str,
        files: Iterable[str | Path] = (),
    ) -> LegacyPageResponse:
        return self._web().post_comment(
            object_type=object_type,
            object_id=object_id,
            uid=uid,
            actioncomment=actioncomment,
            files=files,
        )

    def upload_inline_image(
        self,
        *,
        object_type: str,
        object_id: int,
        uid: str,
        file: str | Path,
    ) -> LegacyPageResponse | InlineUpload:
        response = self._web().upload_inline_image(
            object_type=object_type,
            object_id=object_id,
            uid=uid,
            file=file,
        )
        # Keep malformed responses raw for the service's unknown-result path;
        # a parsed URL must be checked before it can enter a comment body.
        try:
            upload = parse_inline_upload_response(response)
        except ValueError:
            return response
        self._validate_inline_url(upload.url)
        return upload

    def _validate_inline_url(self, value: str) -> None:
        base_url = self._web().base_url
        resolved = urljoin(base_url.rstrip("/") + "/", value)
        parsed = urlsplit(resolved)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("内嵌图片 URL 不允许包含用户凭据")
        if page_origin(resolved) != page_origin(base_url):
            raise ValueError("内嵌图片 URL 必须与 ZenTao 页面同源")

    def snapshot(self, *, object_type: str, object_id: int) -> CommentSnapshot:
        detail = self._read_api_detail(object_type=object_type, object_id=object_id)
        payload = unwrap_detail(detail, object_type)
        if isinstance(payload, dict) and _has_action_collection(payload):
            return snapshot_from_detail(payload, object_type=object_type)
        # Some 21.7.8 API views omit actions; use the fixed detail page then.
        page = self._web().get_object_detail(object_type=object_type, object_id=object_id)
        return parse_page_snapshot(page.body, object_type=object_type)

    def _read_api_detail(self, *, object_type: str, object_id: int) -> object | None:
        path_template = _API_DETAIL_PATHS.get(object_type)
        if path_template is None:
            return None
        return self.session.get(path_template.format(id=object_id))

    def _web(self) -> LegacyWebClient:
        if self._web_client is not None:
            return self._web_client
        config = getattr(self.session, "config", None)
        values = (getattr(config, "base_url", None), getattr(config, "account", None), getattr(config, "password", None))
        if not all(isinstance(value, str) and value for value in values):
            raise ApiError("无法安全建立 ZenTao 页面会话", {"stage": "config"})
        self._web_client = self.web_client_factory(base_url=values[0], account=values[1], password=values[2])
        return self._web_client


def parse_inline_upload_response(response: LegacyPageResponse) -> InlineUpload:
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("内嵌图片上传响应不是有效 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("内嵌图片上传响应不是对象")
    if str(payload.get("result", "")).lower() == "fail" or str(payload.get("status", "")).lower() in {"fail", "error"}:
        raise ValueError("内嵌图片上传返回失败")
    if payload.get("error") not in {None, 0, "0", False}:
        raise ValueError("内嵌图片上传返回失败")
    nested = payload.get("file")
    if isinstance(nested, dict):
        payload = {**nested, **payload}
    raw_file_id = payload.get("fileID", payload.get("fileId", payload.get("id")))
    raw_url = payload.get("url", payload.get("path", payload.get("filePath")))
    if raw_file_id is None and isinstance(raw_url, str):
        query = parse_qs(urlsplit(raw_url).query)
        raw_file_id = next((values[0] for key in ("fileID", "fileId", "id") if (values := query.get(key))), None)
    try:
        file_id = int(raw_file_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("内嵌图片上传响应缺少有效 fileID") from exc
    if file_id <= 0 or not isinstance(raw_url, str) or not raw_url.strip():
        raise ValueError("内嵌图片上传响应缺少有效图片 URL")
    return InlineUpload(file_id=file_id, url=raw_url.strip())


def append_inline_image(comment: str, url: str) -> str:
    return f'{comment}<p><img src="{html.escape(url, quote=True)}"></p>'


def unwrap_detail(detail: object, object_type: str) -> object:
    if not isinstance(detail, dict):
        return detail
    if _has_action_collection(detail):
        return detail
    for key in (object_type, object_type.replace("-", "")):
        value = detail.get(key)
        if isinstance(value, dict):
            return value
    data = detail.get("data")
    return unwrap_detail(data, object_type) if isinstance(data, dict) else detail


def snapshot_from_detail(detail: object, *, object_type: str) -> CommentSnapshot:
    payload = unwrap_detail(detail, object_type)
    if not isinstance(payload, dict):
        raise ApiError("ZenTao 对象详情不是可解析对象，无法进行评论回读", {"object_type": object_type, "stage": "readback"})
    raw_actions = payload.get("actions")
    if isinstance(raw_actions, list):
        actions = [dict(item) for item in raw_actions if isinstance(item, dict)]
    elif isinstance(raw_actions, dict):
        actions = [dict(raw_actions)] if _looks_like_action(raw_actions) else [dict(item) for item in raw_actions.values() if isinstance(item, dict)]
    else:
        actions = []
    critical_payload = next(
        (payload[key] for key in (object_type, object_type.replace("-", "")) if isinstance(payload.get(key), dict)),
        payload,
    )
    critical = {field: critical_payload[field] for field in CRITICAL_FIELDS.get(object_type, ()) if field in critical_payload}
    return CommentSnapshot(tuple(actions), critical)


def extract_actions(detail: object, *, object_type: str) -> list[dict[str, Any]]:
    return list(snapshot_from_detail(detail, object_type=object_type).actions)


def _has_action_collection(value: dict[str, Any]) -> bool:
    return isinstance(value.get("actions"), (list, dict))


def _looks_like_action(value: dict[str, Any]) -> bool:
    return any(key in value for key in ("id", "actionID", "actionId")) and any(
        key in value for key in ("action", "objectType", "objectID", "objectId", "comment")
    )


def page_origin(value: str) -> tuple[str, str, int]:
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port or (443 if scheme == "https" else 80)
    return scheme, host, port


def _action_id(action: dict[str, Any]) -> int | None:
    for key in ("id", "actionID", "actionId"):
        try:
            value = int(action.get(key))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return None


def _normalize_object_type(value: object) -> str:
    return str(value or "").strip().lower().replace("_", "").replace("-", "")


def _action_object_id(action: dict[str, Any]) -> int | None:
    for key in ("objectID", "objectId", "object_id"):
        try:
            value = int(action.get(key))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return None


def _action_value(action: dict[str, Any], keys: tuple[str, ...]) -> object | None:
    for key in keys:
        if key not in action:
            continue
        value = action[key]
        if isinstance(value, dict):
            for nested in ("raw", "html", "content", "text", "value"):
                if nested in value:
                    return value[nested]
        return value
    return None


def _action_actor(action: dict[str, Any]) -> str | None:
    value = _action_value(action, ("actor", "account", "user", "author", "openedBy"))
    if isinstance(value, dict):
        value = value.get("account", value.get("name"))
    return str(value).strip() if isinstance(value, (str, int)) and str(value).strip() else None


def _normalize_comment(value: object) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"\s*/>", ">", re.sub(r"\s+", " ", text).strip())


def _matches_comment(action: dict[str, Any], *, resource: str, object_id: int, comment: str, account: str | None) -> bool:
    if str(_action_value(action, ("action", "actionType", "type")) or "").strip().lower() != "commented":
        return False
    if _normalize_object_type(_action_value(action, ("objectType", "object_type"))) != _normalize_object_type(resource):
        return False
    if _action_object_id(action) != object_id:
        return False
    actor = _action_actor(action)
    if account and actor and actor != account:
        return False
    actual, expected = _normalize_comment(_action_value(action, ("comment", "actioncomment", "content", "remark"))), _normalize_comment(comment)
    return actual == expected or (
        "<img" in expected.lower() and _normalize_markup_for_match(actual) == _normalize_markup_for_match(expected)
    )


def _normalize_markup_for_match(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(
        r"<img\b[^>]*\bsrc\s*=\s*([\"'])(.*?)\1[^>]*>",
        lambda match: f'<img src="{match.group(2)}">',
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"<p\b[^>]*>\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*</p>", "", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip()


def _file_entries(action: dict[str, Any]) -> list[dict[str, Any]]:
    raw = action.get("files")
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    if not isinstance(raw, dict):
        return []
    if any(key in raw for key in ("id", "fileID", "fileId", "name", "title", "fileName", "filename")):
        return [dict(raw)]
    entries: list[dict[str, Any]] = []
    for key, item in raw.items():
        if isinstance(item, dict):
            value = dict(item)
            value.setdefault("id", key)
            entries.append(value)
    return entries


def _file_id(value: dict[str, Any]) -> int | None:
    for key in ("id", "fileID", "fileId"):
        try:
            result = int(value.get(key))
        except (TypeError, ValueError):
            continue
        if result > 0:
            return result
    return None


def verify_attachments(action: dict[str, Any], *, files: tuple[Path, ...], file_sizes: tuple[int, ...]) -> list[int] | None:
    if not files:
        return []
    action_id = _action_id(action)
    if action_id is None:
        return None
    entries, used, result = _file_entries(action), set(), []
    for path, expected_size in zip(files, file_sizes):
        found_id: int | None = None
        for entry in entries:
            entry_id = _file_id(entry)
            if entry_id is None or entry_id in used:
                continue
            if _normalize_object_type(entry.get("objectType", entry.get("object_type"))) != "comment":
                continue
            try:
                owner_id = int(entry.get("objectID", entry.get("objectId", 0)))
            except (TypeError, ValueError):
                continue
            name = next((entry.get(key) for key in ("title", "name", "fileName", "filename") if entry.get(key)), None)
            try:
                size = int(entry.get("size"))
            except (TypeError, ValueError):
                continue
            if owner_id == action_id and name == path.name and size == expected_size:
                found_id = entry_id
                break
        if found_id is None:
            return None
        used.add(found_id)
        result.append(found_id)
    return result


def critical_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        field: {"before": before[field], "after": after[field]}
        for field in sorted(set(before) & set(after))
        if not critical_values_equal(before[field], after[field])
    }


def critical_values_equal(before: object, after: object) -> bool:
    if before == after:
        return True
    if isinstance(before, bool) or isinstance(after, bool):
        return False
    if isinstance(before, (int, float)) and isinstance(after, str):
        try:
            return before == int(after.strip())
        except ValueError:
            return False
    if isinstance(after, (int, float)) and isinstance(before, str):
        try:
            return after == int(before.strip())
        except ValueError:
            return False
    if isinstance(before, dict) and isinstance(after, dict):
        return before.keys() == after.keys() and all(critical_values_equal(before[key], after[key]) for key in before)
    if isinstance(before, (list, tuple)) and isinstance(after, (list, tuple)):
        return len(before) == len(after) and all(critical_values_equal(left, right) for left, right in zip(before, after))
    return False
