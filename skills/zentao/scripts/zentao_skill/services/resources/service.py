from __future__ import annotations

import mimetypes
import os
import uuid
from email.message import Message
from pathlib import Path
from typing import Any

from ...internal.config import ensure_private_directory, resolve_runtime_paths
from ...internal.errors import ResourceFetchError, ResourceSecurityError, ZentaoError
from ...internal.zentao.resources import RESOURCE_OBJECT_TYPES, ResourcesAPI, decode_data_uri, discover_resources, display_source, source_file_name


class ResourcesService:
    OBJECT_TYPES = RESOURCE_OBJECT_TYPES

    def __init__(self, api: ResourcesAPI) -> None:
        self.api = api

    def fetch(self, *, object_type: str, object_id: int) -> dict[str, object]:
        detail = self.api.view_object(object_type=object_type, item_id=object_id)
        candidates, failures = discover_resources(detail)
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
                    metadata = self.api.download(source=candidate.source, destination=temp_path)
                file_name = self._choose_file_name(candidate.file_name, metadata, index)
                destination = self._unique_destination(output_dir, file_name)
                output_dir.mkdir(parents=True, exist_ok=True)
                os.replace(temp_path, destination)
                resources.append({
                    "source": display_source(candidate.source),
                    "origin": candidate.origin,
                    "field": candidate.field,
                    "file_name": destination.name,
                    "content_type": str(metadata.get("content_type") or "application/octet-stream"),
                    "size": int(metadata.get("size") or destination.stat().st_size),
                    "local_path": str(destination),
                })
            except ZentaoError as exc:
                temp_path.unlink(missing_ok=True)
                failures.append(self._failure(display_source(candidate.source), candidate.origin, candidate.field, exc.code, exc.message))
            except (ValueError, OSError) as exc:
                temp_path.unlink(missing_ok=True)
                failures.append(self._failure(display_source(candidate.source), candidate.origin, candidate.field, "RESOURCE_DOWNLOAD_ERROR", str(exc)))

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
    def _failure(source: str, origin: str, field: str | None, code: str, message: str) -> dict[str, object]:
        return {"source": source, "origin": origin, "field": field, "code": code, "message": message}

    def _choose_file_name(self, preferred: str | None, metadata: dict[str, object], index: int) -> str:
        candidates = [preferred, self._content_disposition_name(metadata.get("content_disposition"))]
        source_url = metadata.get("url")
        if isinstance(source_url, str) and not source_url.startswith("data:"):
            candidates.append(source_file_name(source_url))
        for name in candidates:
            safe = self._safe_filename(name)
            if safe:
                return safe
        content_type = str(metadata.get("content_type") or "application/octet-stream").split(";", 1)[0].strip()
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
