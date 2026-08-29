from __future__ import annotations

import mimetypes
import os
import re
import uuid
from email.message import Message
from pathlib import Path
from typing import Any

from ...internal.config import ensure_private_directory, resolve_runtime_paths
from ...internal.errors import ResourceContentError, ResourceFetchError, ResourceSecurityError, ZentaoError
from ...internal.zentao.resources import RESOURCE_OBJECT_TYPES, ResourceCandidate, ResourcesAPI, decode_data_uri, discover_resources, display_source, rewrite_legacy_file_read_url, source_file_name


_HTML_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_GENERIC_CONTENT_TYPES = frozenset({"", "application/octet-stream", "binary/octet-stream"})
_HTML_SUFFIXES = frozenset({".html", ".htm"})
_HTML_ERROR_MARKERS = (
    "fatal error",
    "parse error",
    "uncaught exception",
    "stack trace",
    "login",
    "sign in",
    "登录",
    "请登录",
)
_RESOURCE_SAMPLE_SIZE = 8192


def _content_type(value: object) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _sample_text(sample: bytes) -> str:
    return sample.decode("utf-8", errors="ignore").lstrip("\ufeff \t\r\n").lower()


def _looks_like_html(sample: bytes) -> bool:
    text = _sample_text(sample)
    return bool(re.search(r"<!doctype\s+html\b|<html(?:\s|>)|<(?:head|body|form|br|div|p)(?:\s|>)", text[:_RESOURCE_SAMPLE_SIZE]))


def _has_html_error_marker(sample: bytes) -> bool:
    text = _sample_text(sample)
    return any(marker in text for marker in _HTML_ERROR_MARKERS)


def _is_html_name(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return Path(value).suffix.lower() in _HTML_SUFFIXES


class ResourcesService:
    OBJECT_TYPES = RESOURCE_OBJECT_TYPES

    def __init__(self, api: ResourcesAPI) -> None:
        self.api = api

    def fetch(self, *, object_type: str, object_id: int, include_comments: bool = False) -> dict[str, object]:
        detail = self.api.view_object(object_type=object_type, item_id=object_id)
        candidates, failures = discover_resources(
            detail,
            include_comments=include_comments,
            object_type=object_type,
            object_id=object_id,
        )
        output_dir = self._output_directory(object_type, object_id)
        resources: list[dict[str, object]] = []

        for index, candidate in enumerate(candidates, 1):
            temp_path = output_dir / f".download-{uuid.uuid4().hex}.part"
            try:
                if candidate.source.startswith("data:"):
                    raw, content_type = decode_data_uri(candidate.source)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    temp_path.write_bytes(raw)
                    metadata: dict[str, object] = {
                        "url": candidate.source,
                        "content_type": content_type,
                        "content_disposition": None,
                        "size": len(raw),
                    }
                else:
                    download_source = candidate.source
                    if candidate.origin == "rich_text" or (
                        candidate.origin == "comment" and candidate.field == "actions.comment"
                    ):
                        download_source = rewrite_legacy_file_read_url(candidate.source)
                    metadata = self.api.download(source=download_source, destination=temp_path)
                self._validate_download(candidate, metadata, temp_path)
                file_name = self._choose_file_name(candidate.file_name, metadata, index)
                destination = self._unique_destination(output_dir, file_name)
                output_dir.mkdir(parents=True, exist_ok=True)
                os.replace(temp_path, destination)
                resource = {
                    "source": display_source(candidate.source),
                    "origin": candidate.origin,
                    "field": candidate.field,
                    "file_name": destination.name,
                    "content_type": str(metadata.get("content_type") or "application/octet-stream"),
                    "size": int(metadata.get("size") or destination.stat().st_size),
                    "local_path": str(destination),
                }
                if candidate.action_id is not None:
                    resource["action_id"] = candidate.action_id
                if candidate.file_id is not None:
                    resource["file_id"] = candidate.file_id
                resources.append(resource)
            except ZentaoError as exc:
                temp_path.unlink(missing_ok=True)
                failures.append(
                    self._failure(
                        display_source(candidate.source),
                        candidate.origin,
                        candidate.field,
                        exc.code,
                        exc.message,
                        action_id=candidate.action_id,
                        file_id=candidate.file_id,
                    )
                )
            except (ValueError, OSError) as exc:
                temp_path.unlink(missing_ok=True)
                failures.append(
                    self._failure(
                        display_source(candidate.source),
                        candidate.origin,
                        candidate.field,
                        "RESOURCE_DOWNLOAD_ERROR",
                        str(exc),
                        action_id=candidate.action_id,
                        file_id=candidate.file_id,
                    )
                )

        result = {
            "object_type": object_type,
            "object_id": object_id,
            "resources": resources,
            "partial_failures": failures,
        }
        if not resources and failures:
            raise ResourceFetchError("对象关联资源全部获取失败", result)
        return result

    @classmethod
    def _output_directory(cls, object_type: str, object_id: int) -> Path:
        runtime_paths = resolve_runtime_paths()
        if runtime_paths.scope == "user":
            ensure_private_directory(runtime_paths.temp_root.parent)
        ensure_private_directory(runtime_paths.temp_root)
        root = runtime_paths.temp_root.resolve()
        current = runtime_paths.temp_root
        for name in ("zentao-resources", f"{object_type}-{object_id}"):
            current = current / name
            if current.is_symlink():
                raise ResourceSecurityError("资源临时目录不能是符号链接", {"path": str(current)})
            if current.exists():
                resolved = current.resolve()
                if not resolved.is_relative_to(root):
                    raise ResourceSecurityError("资源临时目录必须位于当前 runtime temp 根内", {"path": str(current)})
                if not resolved.is_dir():
                    raise ResourceSecurityError("资源临时路径必须是目录", {"path": str(current)})
                current = resolved
                continue
            current.mkdir(mode=0o700)
            ensure_private_directory(current)
        resolved = current.resolve()
        if not resolved.is_relative_to(root):
            raise ResourceSecurityError("资源临时目录必须位于当前 runtime temp 根内", {"path": str(current)})
        return resolved

    @staticmethod
    def _failure(
        source: str,
        origin: str,
        field: str | None,
        code: str,
        message: str,
        *,
        action_id: int | None = None,
        file_id: int | None = None,
    ) -> dict[str, object]:
        result: dict[str, object] = {"source": source, "origin": origin, "field": field, "code": code, "message": message}
        if action_id is not None:
            result["action_id"] = action_id
        if file_id is not None:
            result["file_id"] = file_id
        return result

    @classmethod
    def _validate_download(cls, candidate: ResourceCandidate, metadata: dict[str, object], path: Path) -> None:
        size = path.stat().st_size
        content_type = _content_type(metadata.get("content_type"))
        if size == 0:
            raise ResourceContentError("资源响应内容为空", {"content_type": content_type, "size": size})

        with path.open("rb") as stream:
            sample = stream.read(_RESOURCE_SAMPLE_SIZE)
        looks_like_html = _looks_like_html(sample)
        explicit_html = (
            _is_html_name(candidate.file_name)
            or _is_html_name(source_file_name(candidate.source))
            or _is_html_name(cls._content_disposition_name(metadata.get("content_disposition")))
        )
        if candidate.source.startswith("data:"):
            media_type = candidate.source[5:].split(",", 1)[0].split(";", 1)[0].strip().lower()
            explicit_html = explicit_html or media_type in _HTML_CONTENT_TYPES

        html_response = content_type in _HTML_CONTENT_TYPES or looks_like_html
        if html_response and (not explicit_html or _has_html_error_marker(sample)):
            raise ResourceContentError(
                "资源响应疑似 HTML 登录页或错误页",
                {"content_type": content_type, "size": size},
            )

        expected_types: set[str] = set()
        if candidate.source.startswith("data:"):
            media_type = candidate.source[5:].split(",", 1)[0].split(";", 1)[0].strip().lower()
            if "/" in media_type:
                expected_types.add(media_type)
        for name in (
            candidate.file_name,
            cls._content_disposition_name(metadata.get("content_disposition")),
            source_file_name(candidate.source),
        ):
            if not isinstance(name, str):
                continue
            guessed = mimetypes.guess_type(name)[0]
            if guessed:
                expected_types.add(guessed.lower())
        if expected_types and content_type not in _GENERIC_CONTENT_TYPES:
            compatible = content_type in expected_types or (
                content_type in _HTML_CONTENT_TYPES and bool(expected_types & _HTML_CONTENT_TYPES)
            )
            if not compatible:
                raise ResourceContentError(
                    "资源响应 MIME 与资源类型提示不一致",
                    {"content_type": content_type, "expected_content_types": sorted(expected_types)},
                )

    def _choose_file_name(self, preferred: str | None, metadata: dict[str, object], index: int) -> str:
        content_type = _content_type(metadata.get("content_type")) or "application/octet-stream"
        candidates = [preferred, self._content_disposition_name(metadata.get("content_disposition"))]
        source_url = metadata.get("url")
        if isinstance(source_url, str) and not source_url.startswith("data:"):
            candidates.append(source_file_name(source_url, content_type=content_type))
        for name in candidates:
            safe = self._safe_filename(name)
            if safe:
                return safe
        suffix = mimetypes.guess_extension(content_type) or ""
        return f"resource-{index}{suffix}"

    @staticmethod
    def _content_disposition_name(value: object) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        message = Message()
        message["Content-Disposition"] = value
        return message.get_filename()

    @staticmethod
    def _safe_filename(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        name = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
        invalid = '<>:"|?*'
        name = "".join("_" if ord(char) < 32 or char in invalid else char for char in name).replace("\x00", "")
        name = name.rstrip(". ")
        if name in {"", ".", ".."}:
            return None
        stem = Path(name).stem.upper()
        if stem in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
            name = "_" + name
        if len(name) > 240:
            suffix = Path(name).suffix
            keep = max(1, 240 - len(suffix))
            name = name[:keep] + suffix
        return name

    @staticmethod
    def _unique_destination(directory: Path, file_name: str) -> Path:
        candidate = directory / file_name
        if not candidate.exists():
            return candidate
        stem = Path(file_name).stem
        suffix = Path(file_name).suffix
        number = 2
        while True:
            candidate = directory / f"{stem}-{number}{suffix}"
            if not candidate.exists():
                return candidate
            number += 1
