from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Iterable

from ...internal.errors import ApiError, UnknownWriteResult, UsageError, ZentaoError
from ...internal.http.legacy import LegacyPageFailure
from ...internal.zentao.comments import (
    CommentAPI,
    CommentSnapshot,
    InlineUpload,
    _action_id,
    _matches_comment,
    append_inline_image,
    critical_changes,
    is_allowed,
    parse_inline_upload_response,
    verify_attachments,
)


class CommentService:
    """Execute one standalone comment write with deterministic readback."""

    def __init__(self, api: CommentAPI, *, account: str | None = None) -> None:
        self.api = api
        self.account = account

    def add(
        self,
        *,
        resource: str,
        object_id: int,
        comment: str,
        files: Iterable[str | Path] = (),
        inline_image: str | Path | None = None,
        inline_images: Iterable[str | Path] = (),
    ) -> dict[str, object]:
        requested_inline_images = tuple(inline_images)
        if inline_image is not None:
            if requested_inline_images:
                raise UsageError("inline_image 与 inline_images 不能同时使用")
            requested_inline_images = (inline_image,)
        normalized_files, file_sizes = self._validate_input(
            resource=resource,
            object_id=object_id,
            comment=comment,
            files=files,
            inline_images=requested_inline_images,
        )
        try:
            uid = self.api.get_comment_form(object_type=resource, object_id=object_id)
        except ZentaoError as exc:
            raise ApiError(
                "无法读取 ZenTao 评论表单，未执行评论写入",
                {"object_type": resource, "object_id": object_id, "stage": "comment_form", "error_code": exc.code},
            ) from exc
        except LegacyPageFailure as exc:
            raise ApiError(
                "无法读取 ZenTao 评论表单，未执行评论写入",
                {"object_type": resource, "object_id": object_id, "stage": exc.stage},
            ) from exc
        if not isinstance(uid, str) or not uid.strip():
            raise ApiError(
                "ZenTao 评论表单未返回有效 uid，未执行评论写入",
                {"object_type": resource, "object_id": object_id, "stage": "comment_form"},
            )

        before = self._read_snapshot(resource, object_id, stage="before_readback")
        uploaded_by_path: dict[Path, InlineUpload] = {}
        inline_values: list[InlineUpload] = []
        for image in requested_inline_images:
            path = Path(image).resolve()
            if path not in uploaded_by_path:
                uploaded_by_path[path] = self._upload_inline_image(resource, object_id, uid, path)
            # Keep one reference per user argument while reusing the same
            # remote identity when the same local image is repeated.
            inline_values.append(uploaded_by_path[path])
        inlines = tuple(inline_values)
        # The page endpoint consumes HTML. User-supplied comment text must be
        # encoded first so angle characters remain text; only the controlled
        # inline-image fragment is appended as markup below.
        safe_comment = escape(comment, quote=False)
        action_comment = safe_comment
        for inline in inlines:
            action_comment = append_inline_image(action_comment, inline.url)
        post_error: LegacyPageFailure | None = None
        try:
            # This is the only action/comment POST for this invocation.
            self.api.post_comment(
                object_type=resource,
                object_id=object_id,
                uid=uid,
                actioncomment=action_comment,
                files=normalized_files,
            )
        except LegacyPageFailure as exc:
            post_error = exc

        try:
            after = self._read_snapshot(resource, object_id, stage="after_readback")
        except (ZentaoError, LegacyPageFailure) as exc:
            error_code = exc.code if isinstance(exc, ZentaoError) else exc.stage
            raise UnknownWriteResult(
                "页面评论已提交，但无法完成回读确认",
                {
                    "object_type": resource,
                    "object_id": object_id,
                    "stage": "after_readback",
                    "error_code": error_code,
                    **({"possible_orphan": True} if inlines else {}),
                },
            ) from exc

        result = self._confirm(
            resource=resource,
            object_id=object_id,
            comment=action_comment,
            before=before,
            after=after,
            files=normalized_files,
            file_sizes=file_sizes,
            inlines=inlines,
        )
        if result is None:
            details: dict[str, object] = {
                "object_type": resource,
                "object_id": object_id,
                "stage": "after_readback",
                "post_transport_uncertain": bool(post_error and post_error.transport_uncertain),
            }
            if inlines:
                details["possible_orphan"] = True
            raise UnknownWriteResult("无法在新增 action 中唯一确认本次评论，未重放页面写入", details)
        if post_error is not None and not post_error.transport_uncertain:
            result["post_response"] = "error_readback_confirmed"
        return result

    def _upload_inline_image(self, resource: str, object_id: int, uid: str, image: str | Path | None) -> InlineUpload:
        assert image is not None
        try:
            response = self.api.upload_inline_image(
                object_type=resource,
                object_id=object_id,
                uid=uid,
                file=image,
            )
        except LegacyPageFailure as exc:
            if exc.transport_uncertain:
                raise UnknownWriteResult(
                    "内嵌图片上传结果未知，已停止评论写入",
                    {"stage": "inline_upload", "possible_orphan": True},
                ) from exc
            raise ApiError(
                "内嵌图片上传失败，未执行评论写入",
                {"stage": "inline_upload", "status": exc.status},
            ) from exc
        except ValueError as exc:
            raise UnknownWriteResult(
                "内嵌图片上传响应不安全，已停止评论写入",
                {"stage": "inline_upload", "possible_orphan": True},
            ) from exc
        try:
            upload = response if isinstance(response, InlineUpload) else parse_inline_upload_response(response)
        except (TypeError, ValueError) as exc:
            raise UnknownWriteResult(
                "内嵌图片上传响应无法确认，已停止评论写入",
                {"stage": "inline_upload", "possible_orphan": True},
            ) from exc
        return upload

    def _read_snapshot(self, resource: str, object_id: int, *, stage: str) -> CommentSnapshot:
        try:
            value = self.api.snapshot(object_type=resource, object_id=object_id)
        except ZentaoError as exc:
            raise ApiError(
                "无法读取 ZenTao 对象评论回读快照",
                {"object_type": resource, "object_id": object_id, "stage": stage, "error_code": exc.code},
            ) from exc
        except LegacyPageFailure as exc:
            raise ApiError(
                "无法读取 ZenTao 对象评论回读快照",
                {"object_type": resource, "object_id": object_id, "stage": stage, "error_code": exc.stage},
            ) from exc
        if isinstance(value, CommentSnapshot):
            return value
        if isinstance(value, dict):
            raw_actions = value.get("actions", ())
            actions = tuple(item for item in raw_actions if isinstance(item, dict)) if isinstance(raw_actions, (list, tuple)) else ()
            critical = value.get("critical_fields", value.get("critical", {}))
            return CommentSnapshot(actions, dict(critical) if isinstance(critical, dict) else {})
        raise ApiError(
            "ZenTao 评论回读快照格式无效",
            {"object_type": resource, "object_id": object_id, "stage": stage},
        )

    @staticmethod
    def _validate_input(
        *,
        resource: str,
        object_id: int,
        comment: str,
        files: Iterable[str | Path],
        inline_images: tuple[str | Path, ...],
    ) -> tuple[tuple[Path, ...], tuple[int, ...]]:
        if not is_allowed(resource, "comment"):
            raise UsageError("当前对象不支持 standalone comment", {"object_type": resource, "capability": "comment"})
        if not isinstance(object_id, int) or isinstance(object_id, bool) or object_id <= 0:
            raise UsageError("评论对象 ID 必须是正整数")
        if not isinstance(comment, str) or not comment.strip():
            raise UsageError("评论正文不能为空")
        try:
            file_values = tuple(files)
        except TypeError as exc:
            raise UsageError("--file 参数必须是文件路径列表") from exc
        if file_values and not is_allowed(resource, "attachments"):
            raise UsageError("当前对象不支持评论普通附件", {"object_type": resource, "capability": "attachments"})
        if inline_images and not is_allowed(resource, "inline_image"):
            raise UsageError("当前对象不支持评论内嵌图片", {"object_type": resource, "capability": "inline_image"})
        paths: list[Path] = []
        sizes: list[int] = []
        for value in file_values:
            path = Path(value)
            if not path.is_file():
                raise UsageError(f"评论附件不存在: {path}")
            paths.append(path)
            sizes.append(path.stat().st_size)
        for inline_image in inline_images:
            if not Path(inline_image).is_file():
                raise UsageError(f"内嵌图片不存在: {inline_image}")
        return tuple(paths), tuple(sizes)

    def _confirm(
        self,
        *,
        resource: str,
        object_id: int,
        comment: str,
        before: CommentSnapshot,
        after: CommentSnapshot,
        files: tuple[Path, ...],
        file_sizes: tuple[int, ...],
        inlines: tuple[InlineUpload, ...],
    ) -> dict[str, object] | None:
        before_ids = {_action_id(item) for item in before.actions}
        before_ids.discard(None)
        new_actions = [item for item in after.actions if _action_id(item) not in before_ids and _action_id(item) is not None]
        candidates = [
            item for item in new_actions
            if _matches_comment(item, resource=resource, object_id=object_id, comment=comment, account=self.account)
        ]
        valid: list[tuple[dict[str, Any], list[int]]] = []
        for candidate in candidates:
            ids = verify_attachments(candidate, files=files, file_sizes=file_sizes)
            if ids is not None:
                valid.append((candidate, ids))
        if len(valid) != 1:
            return None
        candidate, file_ids = valid[0]
        action_id = _action_id(candidate)
        if action_id is None:
            return None
        result: dict[str, object] = {
            "status": "success",
            "object_type": resource,
            "object_id": object_id,
            "action_id": action_id,
            "action": "commented",
        }
        if files:
            result["file_ids"] = file_ids
        if len(inlines) == 1:
            result["inline_file_id"] = inlines[0].file_id
            result["inline_image_url"] = inlines[0].url
        elif inlines:
            result["inline_file_ids"] = [inline.file_id for inline in inlines]
            result["inline_image_urls"] = [inline.url for inline in inlines]
        changes = critical_changes(before.critical_fields, after.critical_fields)
        if changes:
            result["concurrent_changes"] = changes
        return result
