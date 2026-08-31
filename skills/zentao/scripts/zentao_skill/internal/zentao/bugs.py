from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

from ..errors import ApiError, UnknownWriteResult, UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from ..http.legacy import LegacyPageFailure, LegacyWebClient
from .bug_steps import (
    InlineUpload,
    bug_detail,
    contains_inline_reference,
    create_form_fields,
    edit_form_fields,
    extract_bug_id,
    hidden_value,
    owns_inline_file,
    positive_id,
    render_steps,
    unique_uploads,
    validate_inline_images,
)
from .comments import page_origin, parse_inline_upload_response
from .session import ZentaoSession


class BugsAPI:
    ENDPOINT_IDS = frozenset({'bug.create', 'bug.list_project', 'bug.activate', 'bug.delete', 'bug.edit', 'bug.list_execution', 'bug.list_product', 'bug.resolve', 'bug.close', 'bug.view'})

    def __init__(self, session: ZentaoSession, *, web_client_factory: Any = LegacyWebClient) -> None:
        self.session = session
        self.web_client_factory = web_client_factory
        self._web_client: LegacyWebClient | None = None

    @endpoint('bug.create')
    def create(self, *, affected_build: list[object] | None, product: object | None, title: object | None, assignee: object | None = None, branch: object | None = None, browser: object | None = None, deadline: object | None = None, execution: object | None = None, keywords: object | None = None, module: object | None = None, os: object | None = None, priority: object | None = None, project: object | None = None, severity: object | None = None, steps: object | None = None, steps_inline_images: Iterable[str | Path] = (), story: object | None = None, task: object | None = None, type: object | None = None) -> object | None:
        inline_images = validate_inline_images(steps_inline_images)
        if inline_images:
            return self._create_with_inline_images(
                product=product,
                title=title,
                affected_build=affected_build,
                branch=branch,
                browser=browser,
                deadline=deadline,
                execution=execution,
                keywords=keywords,
                module=module,
                os=os,
                priority=priority,
                project=project,
                severity=severity,
                steps=steps,
                story=story,
                task=task,
                type=type,
                assignee=assignee,
                inline_images=inline_images,
            )
        body = compact_dict({
            'productID': map_enum('productID', product),
            # ZenTao 21.7.8 requires the legacy compatibility alias as well
            # as the documented productID field for Bug creation.
            'product': map_enum('product', product),
            'title': map_enum('title', title),
            'openedBuild': map_enum('openedBuild', affected_build),
            'branch': map_enum('branch', branch),
            'module': map_enum('module', module),
            'project': map_enum('project', project),
            'execution': map_enum('execution', execution),
            'story': map_enum('story', story),
            'task': map_enum('task', task),
            'severity': map_enum('severity', severity),
            'pri': map_enum('pri', priority),
            'type': map_enum('type', type),
            'os': map_enum('os', os),
            'browser': map_enum('browser', browser),
            'steps': map_enum('steps', steps),
            'assignedTo': map_enum('assignedTo', assignee),
            'deadline': map_enum('deadline', deadline),
            'keywords': map_enum('keywords', keywords),
        })
        return self.session.post('/bugs', body=body)

    @endpoint('bug.edit')
    def edit(self, *, item_id: int, affected_build: list[object] | None = None, execution: object | None = None, priority: object | None = None, project: object | None = None, severity: object | None = None, steps: object | None = None, steps_inline_images: Iterable[str | Path] = (), story: object | None = None, title: object | None = None, type: object | None = None) -> object | None:
        inline_images = validate_inline_images(steps_inline_images)
        if inline_images:
            return self._edit_with_inline_images(
                item_id=item_id,
                affected_build=affected_build,
                execution=execution,
                priority=priority,
                project=project,
                severity=severity,
                steps=steps,
                story=story,
                title=title,
                type=type,
                inline_images=inline_images,
            )
        body = compact_dict({
            'title': map_enum('title', title),
            'severity': map_enum('severity', severity),
            'pri': map_enum('pri', priority),
            'type': map_enum('type', type),
            'openedBuild': map_enum('openedBuild', affected_build),
            'steps': map_enum('steps', steps),
            'project': map_enum('project', project),
            'execution': map_enum('execution', execution),
            'story': map_enum('story', story),
        })
        return self.session.put(f'/bugs/{item_id}', body=body)

    def _create_with_inline_images(
        self,
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
        steps: object | None,
        story: object | None,
        task: object | None,
        type: object | None,
        assignee: object | None,
        inline_images: tuple[Path, ...],
    ) -> object:
        product_id = positive_id(product, "product")
        try:
            form = self._web().get_bug_create_form(product_id=product_id)
        except LegacyPageFailure as exc:
            self._raise_legacy_write_failure(exc, operation="create", bug_id=None)
        uid = hidden_value(form, "uid")
        if not uid:
            raise ApiError("ZenTao Bug 创建表单缺少 uid，未执行 Bug 写入", {"stage": "bug_create_form"})
        uploads = self._upload_steps_images(inline_images, uid=uid, product_id=product_id)
        rendered_steps = render_steps(steps, uploads)
        fields = create_form_fields(
            product=product,
            title=title,
            affected_build=affected_build,
            branch=branch,
            browser=browser,
            deadline=deadline,
            execution=execution,
            keywords=keywords,
            module=module,
            os=os,
            priority=priority,
            project=project,
            severity=severity,
            steps=rendered_steps,
            story=story,
            task=task,
            type=type,
            assignee=assignee,
            uid=uid,
        )
        try:
            response = self._web().post_bug_form(form=form, fields=fields, product_id=product_id)
        except LegacyPageFailure as exc:
            self._raise_legacy_write_failure(exc, operation="create", bug_id=None)
        bug_id = extract_bug_id(response)
        if bug_id is None:
            raise UnknownWriteResult("ZenTao Bug 创建响应缺少可回读的 Bug ID，未再次提交")
        return self._readback_steps(bug_id, rendered_steps, uploads, operation="create")

    def _edit_with_inline_images(
        self,
        *,
        item_id: int,
        affected_build: list[object] | None,
        execution: object | None,
        priority: object | None,
        project: object | None,
        severity: object | None,
        steps: object | None,
        story: object | None,
        title: object | None,
        type: object | None,
        inline_images: tuple[Path, ...],
    ) -> object:
        current = bug_detail(self.view(item_id=item_id), item_id)
        try:
            form = self._web().get_bug_edit_form(bug_id=item_id)
        except LegacyPageFailure as exc:
            self._raise_legacy_write_failure(exc, operation="edit", bug_id=item_id)
        uid = hidden_value(form, "uid")
        if not uid:
            raise ApiError("ZenTao Bug 编辑表单缺少 uid，未执行 Bug 写入", {"object_id": item_id, "stage": "bug_edit_form"})
        uploads = self._upload_steps_images(inline_images, uid=uid, bug_id=item_id)
        base_steps = steps if steps is not None else current.get("steps", "")
        rendered_steps = render_steps(base_steps, uploads)
        fields = edit_form_fields(
            current,
            bug_id=item_id,
            form=form,
            affected_build=affected_build,
            execution=execution,
            priority=priority,
            project=project,
            severity=severity,
            steps=rendered_steps,
            story=story,
            title=title,
            type=type,
            uid=uid,
        )
        try:
            response = self._web().post_bug_form(form=form, fields=fields, bug_id=item_id)
        except LegacyPageFailure as exc:
            if exc.transport_uncertain:
                try:
                    return self._readback_steps(item_id, rendered_steps, uploads, operation="edit")
                except Exception:
                    pass
            self._raise_legacy_write_failure(exc, operation="edit", bug_id=item_id)
        return self._readback_steps(item_id, rendered_steps, uploads, operation="edit")

    def _upload_steps_images(
        self,
        images: tuple[Path, ...],
        *,
        uid: str,
        product_id: int | None = None,
        bug_id: int | None = None,
    ) -> tuple[InlineUpload, ...]:
        uploads_by_path: dict[Path, InlineUpload] = {}
        for image in images:
            if image in uploads_by_path:
                continue
            try:
                response = self._web().upload_bug_steps_image(
                    uid=uid,
                    file=image,
                    product_id=product_id,
                    bug_id=bug_id,
                )
                upload = parse_inline_upload_response(response)
                self._validate_inline_url(upload.url)
            except LegacyPageFailure as exc:
                if exc.transport_uncertain:
                    raise UnknownWriteResult(
                        "Bug 步骤图片上传结果未知，未执行 Bug 写入",
                        {"stage": exc.stage, "possible_orphan": True},
                    ) from exc
                raise ApiError(
                    "Bug 步骤图片上传失败，未执行 Bug 写入",
                    {"stage": exc.stage, "status": exc.status},
                ) from exc
            except (ValueError, ApiError) as exc:
                raise UnknownWriteResult(
                    "Bug 步骤图片上传响应无法安全确认，未执行 Bug 写入",
                    {"stage": "inline_upload", "possible_orphan": True},
                ) from exc
            uploads_by_path[image] = upload
        return tuple(uploads_by_path[image] for image in images)

    def _readback_steps(
        self,
        bug_id: int,
        expected_steps: str,
        uploads: tuple[InlineUpload, ...],
        *,
        operation: str,
    ) -> object:
        try:
            result = self.view(item_id=bug_id)
            detail = bug_detail(result, bug_id)
        except Exception as exc:
            raise UnknownWriteResult(
                "Bug 写入已提交，但无法完成步骤图片回读确认",
                {"object_type": "bug", "object_id": bug_id, "operation": operation},
            ) from exc
        actual_steps = str(detail.get("steps") or "")
        expected_text = expected_steps.split("<p><img", 1)[0]
        if expected_text and expected_text not in actual_steps:
            raise ApiError(
                "Bug 写入返回成功但回读步骤文本不一致，未再次提交",
                {"object_type": "bug", "object_id": bug_id, "stage": "steps_readback"},
            )
        if "<img" not in actual_steps.lower() or any(
            not contains_inline_reference(actual_steps, upload) for upload in uploads
        ):
            raise ApiError(
                "Bug 写入返回成功但回读未发现步骤内嵌图片，未再次提交",
                {"object_type": "bug", "object_id": bug_id, "stage": "steps_readback"},
            )
        if any(not owns_inline_file(detail, bug_id, upload) for upload in unique_uploads(uploads)):
            raise ApiError(
                "Bug 步骤图片已写入但资源归属回读不一致，未再次提交",
                {"object_type": "bug", "object_id": bug_id, "stage": "resource_readback"},
            )
        return result

    def _raise_legacy_write_failure(self, exc: LegacyPageFailure, *, operation: str, bug_id: int | None) -> None:
        if exc.transport_uncertain:
            raise UnknownWriteResult(
                "Bug 页面写入结果未知，未再次提交",
                {"object_type": "bug", "object_id": bug_id, "operation": operation, "stage": exc.stage},
            ) from exc
        raise ApiError(
            "Bug 页面表单写入失败，未再次提交",
            {"object_type": "bug", "object_id": bug_id, "operation": operation, "stage": exc.stage, "status": exc.status},
        ) from exc

    def _validate_inline_url(self, value: str) -> None:
        resolved = urljoin(self._web().base_url.rstrip("/") + "/", value)
        parsed = urlsplit(resolved)
        if parsed.username is not None or parsed.password is not None or page_origin(resolved) != page_origin(self._web().base_url):
            raise ValueError("Bug 步骤图片 URL 必须与 ZenTao 页面同源且不包含凭据")

    def _web(self) -> LegacyWebClient:
        if self._web_client is not None:
            return self._web_client
        config = getattr(self.session, "config", None)
        values = (getattr(config, "base_url", None), getattr(config, "account", None), getattr(config, "password", None))
        if not all(isinstance(value, str) and value for value in values):
            raise ApiError("无法安全建立 ZenTao 页面会话", {"stage": "config"})
        self._web_client = self.web_client_factory(base_url=values[0], account=values[1], password=values[2])
        return self._web_client

    @endpoint('bug.list_product')
    def list_product(self, *, product: int, branch: object | None = None, browse: object | None = None, filters: object | None = None, group_join: object | None = None, module: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'branch': map_enum('branch', branch),
            'browseType': map_enum('browseType', browse),
            'module': map_enum('module', module),
            'pageID': map_enum('pageID', page),
            'recPerPage': map_enum('recPerPage', per_page),
            'filters': map_enum('filters', filters),
            'groupJoin': map_enum('groupJoin', group_join),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/products/{product}/bugs', query=query)

    @endpoint('bug.list_project')
    def list_project(self, *, project: int, browse: object | None = None, execution_filter: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, param: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'executionID': map_enum('executionID', execution_filter),
            'browseType': map_enum('browseType', browse),
            'param': map_enum('param', param),
            'pageID': map_enum('pageID', page),
            'recPerPage': map_enum('recPerPage', per_page),
            'filters': map_enum('filters', filters),
            'groupJoin': map_enum('groupJoin', group_join),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/projects/{project}/bugs', query=query)

    @endpoint('bug.list_execution')
    def list_execution(self, *, execution: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, param: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'browseType': map_enum('browseType', browse),
            'param': map_enum('param', param),
            'pageID': map_enum('pageID', page),
            'recPerPage': map_enum('recPerPage', per_page),
            'filters': map_enum('filters', filters),
            'groupJoin': map_enum('groupJoin', group_join),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/executions/{execution}/bugs', query=query)

    @endpoint('bug.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/bugs/{item_id}')

    @endpoint('bug.resolve')
    def resolve(self, *, item_id: int, resolution: object | None, assignee: object | None = None, comment: object | None = None, duplicate_bug: object | None = None, resolved_build: object | None = None, resolved_date: object | None = None) -> object | None:
        body = compact_dict({
            'resolution': map_enum('resolution', resolution),
            'resolvedDate': map_enum('resolvedDate', resolved_date),
            'resolvedBuild': map_enum('resolvedBuild', resolved_build),
            'duplicateBug': map_enum('duplicateBug', duplicate_bug),
            'assignedTo': map_enum('assignedTo', assignee),
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/bugs/{item_id}/resolve', body=body)

    @endpoint('bug.close')
    def close(self, *, item_id: int, comment: object | None = None) -> object | None:
        body = compact_dict({
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/bugs/{item_id}/close', body=body)

    @endpoint('bug.activate')
    def activate(self, *, item_id: int, affected_build: list[object] | None = None, assignee: object | None = None, comment: object | None = None) -> object | None:
        body = compact_dict({
            'openedBuild': map_enum('openedBuild', affected_build),
            'assignedTo': map_enum('assignedTo', assignee),
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/bugs/{item_id}/activate', body=body)

    @endpoint('bug.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/bugs/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
