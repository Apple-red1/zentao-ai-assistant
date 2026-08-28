#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ZENTAO_SCRIPTS = REPO_ROOT / "skills" / "zentao" / "scripts"
ZENTAO_CLI = ZENTAO_SCRIPTS / "zentao.py"
if str(ZENTAO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ZENTAO_SCRIPTS))

from zentao_skill.public import prepare_runtime_temp_root  # noqa: E402


SUPPORTED_TYPES = (
    "bug",
    "epic",
    "execution",
    "feedback",
    "product",
    "product-plan",
    "program",
    "requirement",
    "story",
    "task",
    "test-case",
    "ticket",
    "user",
)
SUPPORTED_TYPE_SET = frozenset(SUPPORTED_TYPES)


class BatchExportError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def parse_object_spec(value: str) -> tuple[str, int]:
    object_type, separator, object_id = value.strip().partition(":")
    if not separator or not object_type or not object_id:
        raise BatchExportError(
            "INVALID_OBJECT_SPEC",
            f"对象必须使用 <type>:<id> 形式: {value}",
            details={"value": value, "supported_types": list(SUPPORTED_TYPES)},
        )
    object_type = object_type.strip()
    object_id = object_id.strip()
    if object_type not in SUPPORTED_TYPE_SET:
        raise BatchExportError(
            "UNSUPPORTED_OBJECT_TYPE",
            f"不支持的 ZenTao 对象类型: {object_type}",
            details={"value": value, "supported_types": list(SUPPORTED_TYPES)},
        )
    try:
        item_id = int(object_id)
    except ValueError as exc:
        raise BatchExportError(
            "INVALID_OBJECT_ID",
            f"对象 ID 必须是正整数: {value}",
            details={"value": value},
        ) from exc
    if item_id <= 0:
        raise BatchExportError(
            "INVALID_OBJECT_ID",
            f"对象 ID 必须是正整数: {value}",
            details={"value": value},
        )
    return object_type, item_id


def normalize_object_specs(values: list[str]) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    for value in values:
        item = parse_object_spec(value)
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _private_dir(path: Path, *, parents: bool = True) -> None:
    path.mkdir(parents=parents, exist_ok=False, mode=0o700)
    if os.name == "posix":
        path.chmod(0o700)


def _ensure_private_subdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        path.chmod(0o700)


def _write_private_text(path: Path, text: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = -1
            handle.write(text)
        if os.name == "posix":
            path.chmod(0o600)
    finally:
        if fd >= 0:
            os.close(fd)


def _longest_backtick_run(text: str) -> int:
    longest = current = 0
    for char in text:
        if char == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def render_content_markdown(object_type: str, object_id: int, payload: object) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
    fence = "`" * max(3, _longest_backtick_run(serialized) + 1)
    return (
        f"# ZenTao {object_type}:{object_id}\n\n"
        f"> 数据来源：`zentao {object_type} view {object_id} --json`。"
        "以下 JSON 为该 `view` 当前实际返回的完整对象数据，不裁剪字段。\n\n"
        "## 完整字段\n\n"
        f"{fence}json\n{serialized}\n{fence}\n"
    )


def render_failed_content_markdown(object_type: str, object_id: int, failure: dict[str, Any]) -> str:
    serialized = json.dumps(failure, ensure_ascii=False, indent=2, sort_keys=False)
    fence = "`" * max(3, _longest_backtick_run(serialized) + 1)
    return (
        f"# ZenTao {object_type}:{object_id}\n\n"
        "> 对象详情读取失败，本文件只记录本次导出失败信息；完整失败清单同时保存在根目录 `manifest.json`。\n\n"
        "## 失败信息\n\n"
        f"{fence}json\n{serialized}\n{fence}\n"
    )


def _decode_cli_error(process: subprocess.CompletedProcess[str], fallback_code: str) -> dict[str, Any]:
    raw = process.stderr.strip()
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            error = dict(payload["error"])
            error.setdefault("code", fallback_code)
            error.setdefault("message", raw)
            error.setdefault("details", {})
            return error
    return {
        "code": fallback_code,
        "message": raw or f"ZenTao CLI 退出码 {process.returncode}",
        "details": {"returncode": process.returncode},
    }


def _run_cli(argv: list[str]) -> tuple[object | None, dict[str, Any] | None]:
    try:
        process = subprocess.run(
            [sys.executable, str(ZENTAO_CLI), *argv, "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, {
            "code": "ZENTAO_CLI_PROCESS_ERROR",
            "message": str(exc),
            "details": {"argv": argv},
        }
    if process.returncode != 0:
        return None, _decode_cli_error(process, "ZENTAO_CLI_ERROR")
    try:
        return json.loads(process.stdout), None
    except json.JSONDecodeError as exc:
        return None, {
            "code": "ZENTAO_CLI_INVALID_JSON",
            "message": f"ZenTao CLI 返回无法解析的 JSON: {exc}",
            "details": {"argv": argv},
        }


def _failure(stage: str, error: dict[str, Any], *, resource: object | None = None) -> dict[str, Any]:
    details = error.get("details")
    item: dict[str, Any] = {
        "stage": stage,
        "code": str(error.get("code") or "EXPORT_ERROR"),
        "reason": str(error.get("message") or error.get("reason") or "未知错误"),
    }
    if resource not in (None, ""):
        item["resource"] = resource
    if details not in (None, {}, []):
        item["details"] = details
    return item


def _resource_failure(item: object) -> dict[str, Any]:
    if not isinstance(item, dict):
        return _failure(
            "resource_download",
            {"code": "RESOURCE_ERROR", "message": str(item), "details": {"raw": item}},
        )
    resource = item.get("file_name") or item.get("source") or item.get("field")
    message = item.get("message") or item.get("reason") or "资源获取失败"
    return _failure(
        "resource_download",
        {
            "code": item.get("code") or "RESOURCE_ERROR",
            "message": message,
            "details": dict(item),
        },
        resource=resource,
    )


def _safe_resource_source(local_path: object, resource_root: Path) -> Path:
    if not isinstance(local_path, str) or not local_path:
        raise BatchExportError("RESOURCE_COPY_ERROR", "资源结果缺少 local_path")
    path = Path(local_path)
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise BatchExportError(
            "RESOURCE_COPY_ERROR",
            f"资源文件不可读取: {path}",
            details={"local_path": str(path), "error": str(exc)},
        ) from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise BatchExportError(
            "RESOURCE_COPY_ERROR",
            f"资源文件必须是普通文件且不能是符号链接: {path}",
            details={"local_path": str(path)},
        )
    try:
        resolved = path.resolve(strict=True)
        trusted = resource_root.resolve(strict=True)
    except OSError as exc:
        raise BatchExportError(
            "RESOURCE_COPY_ERROR",
            f"无法解析资源文件路径: {path}",
            details={"local_path": str(path), "error": str(exc)},
        ) from exc
    if not resolved.is_relative_to(trusted):
        raise BatchExportError(
            "RESOURCE_COPY_ERROR",
            "资源文件不在当前 runtime 的 zentao-resources 目录内",
            details={"local_path": str(resolved), "resource_root": str(trusted)},
        )
    return resolved


def _unique_destination(directory: Path, requested_name: object, fallback: str) -> Path:
    name = Path(str(requested_name or fallback)).name.strip() or fallback
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        candidate = directory / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _copy_resources(
    payload: object,
    destination: Path,
    resource_root: Path,
) -> tuple[int, list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return 0, [
            _failure(
                "resource_fetch",
                {"code": "RESOURCE_RESULT_INVALID", "message": "resource fetch 返回值不是对象", "details": {"payload": payload}},
            )
        ]

    for item in payload.get("partial_failures") or []:
        failures.append(_resource_failure(item))

    copied = 0
    for index, item in enumerate(payload.get("resources") or [], start=1):
        if not isinstance(item, dict):
            failures.append(_resource_failure(item))
            continue
        try:
            source = _safe_resource_source(item.get("local_path"), resource_root)
            target = _unique_destination(destination, item.get("file_name"), f"resource-{index}")
            shutil.copyfile(source, target)
            if os.name == "posix":
                target.chmod(0o600)
            copied += 1
        except (BatchExportError, OSError) as exc:
            if isinstance(exc, BatchExportError):
                error = {"code": exc.code, "message": exc.message, "details": exc.details}
            else:
                error = {"code": "RESOURCE_COPY_ERROR", "message": str(exc), "details": {}}
            failures.append(_failure("resource_copy", error, resource=item.get("file_name") or item.get("source")))
    return copied, failures


def _make_run_paths(temp_root: Path) -> tuple[str, Path, Path, Path]:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    run_id = f"{stamp}-{suffix}"
    base = temp_root / "zentao" / "zentao-batch-export"
    _ensure_private_subdir(base)
    run_dir = base / run_id
    _private_dir(run_dir)
    staging = run_dir / "staging"
    _private_dir(staging, parents=False)
    zip_path = run_dir / f"zentao-export-{run_id}.zip"
    return run_id, run_dir, staging, zip_path


def _write_manifest(staging: Path, manifest: dict[str, Any]) -> Path:
    path = staging / "manifest.json"
    _write_private_text(path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return path


def _build_zip(staging: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(staging.rglob("*")):
            if path.is_symlink():
                raise BatchExportError(
                    "ZIP_SECURITY_ERROR",
                    f"staging 中出现符号链接，拒绝打包: {path}",
                    details={"path": str(path)},
                )
            relative = path.relative_to(staging).as_posix()
            if path.is_dir():
                archive.writestr(relative.rstrip("/") + "/", b"")
            elif path.is_file():
                archive.write(path, relative)
    if os.name == "posix":
        zip_path.chmod(0o600)


def export_objects(specs: list[str]) -> dict[str, Any]:
    objects = normalize_object_specs(specs)
    if not objects:
        raise BatchExportError("EMPTY_EXPORT", "至少需要一个 ZenTao 对象")

    temp_root = prepare_runtime_temp_root()
    run_id, run_dir, staging, zip_path = _make_run_paths(temp_root)
    objects_root = staging / "objects"
    _private_dir(objects_root, parents=False)
    resource_root = temp_root / "zentao-resources"

    manifest_objects: list[dict[str, Any]] = []
    exported_count = 0

    for object_type, object_id in objects:
        relative_path = Path("objects") / object_type / str(object_id)
        object_dir = staging / relative_path
        _ensure_private_subdir(object_dir)
        resources_dir = object_dir / "resources"
        _private_dir(resources_dir, parents=False)
        failures: list[dict[str, Any]] = []

        view_payload, view_error = _run_cli([object_type, "view", str(object_id)])
        if view_error is not None:
            failure = _failure("view", view_error)
            failures.append(failure)
            _write_private_text(object_dir / "content.md", render_failed_content_markdown(object_type, object_id, failure))
        else:
            exported_count += 1
            _write_private_text(object_dir / "content.md", render_content_markdown(object_type, object_id, view_payload))

            resource_payload, resource_error = _run_cli(
                ["resource", "fetch", "--object-type", object_type, "--object-id", str(object_id)]
            )
            resource_count = 0
            if resource_error is not None:
                details = resource_error.get("details") if isinstance(resource_error, dict) else None
                partials = details.get("partial_failures") if isinstance(details, dict) else None
                if isinstance(partials, list) and partials:
                    failures.extend(_resource_failure(item) for item in partials)
                else:
                    failures.append(_failure("resource_fetch", resource_error))
            else:
                resource_count, resource_failures = _copy_resources(resource_payload, resources_dir, resource_root)
                failures.extend(resource_failures)
        if view_error is not None:
            resource_count = 0

        manifest_objects.append(
            {
                "type": object_type,
                "id": object_id,
                "path": relative_path.as_posix(),
                "complete": not failures,
                "resource_count": resource_count,
                "failures": failures,
            }
        )

    manifest = {
        "schema_version": 1,
        "complete": all(item["complete"] for item in manifest_objects),
        "requested_count": len(objects),
        "exported_count": exported_count,
        "objects": manifest_objects,
    }
    manifest_path = _write_manifest(staging, manifest)
    _build_zip(staging, zip_path)

    return {
        "run_id": run_id,
        "complete": manifest["complete"],
        "requested_count": manifest["requested_count"],
        "exported_count": manifest["exported_count"],
        "zip_path": str(zip_path),
        "manifest_path": str(manifest_path),
        "staging_path": str(staging),
    }


def _print_error(error: BatchExportError) -> None:
    print(
        json.dumps(
            {"error": {"code": error.code, "message": error.message, "details": error.details}},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch export ZenTao objects, fields and resources into one ZIP")
    parser.add_argument("objects", nargs="+", metavar="TYPE:ID", help="例如 bug:123 story:78")
    parser.add_argument("--json", action="store_true", help="输出紧凑 JSON")
    args = parser.parse_args(argv)
    try:
        result = export_objects(args.objects)
    except BatchExportError as exc:
        _print_error(exc)
        return 1
    except Exception as exc:
        _print_error(BatchExportError("BATCH_EXPORT_ERROR", str(exc)))
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"ZIP: {result['zip_path']}")
        print(f"complete: {str(result['complete']).lower()}")
        print(f"requested_count: {result['requested_count']}")
        print(f"exported_count: {result['exported_count']}")
        if not result["complete"]:
            print(f"manifest: {result['manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
