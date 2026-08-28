from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from ..errors import ApiError, UnknownWriteResult, UsageError
from ..http.legacy import LegacyPageFailure, LegacyWebClient
from .bugs import BugsAPI
from .common import compact_dict, endpoint, make_order_by, map_enum, require_response_body, validate_pagination
from .session import ZentaoSession


class FilesAPI:
    ENDPOINT_IDS = frozenset({'file.delete', 'file.upload', 'file.edit'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session
        self._bugs = BugsAPI(session)

    @endpoint('file.upload')
    def upload(self, *, file: str | Path, object_id: object | None, object_type: object | None) -> object | None:
        file_path = Path(file)
        multipart = compact_dict({
            'file': file,
            'objectType': object_type,
            'objectID': object_id,
        })
        try:
            return require_response_body(self.session.post('/files', multipart=multipart), endpoint_id='file.upload', feature='文件上传')
        except ApiError as exc:
            if not self._is_empty_v2_upload(exc) or object_type != 'bug':
                raise
            return self._upload_bug_through_legacy_form(
                file_path=file_path,
                bug_id=object_id,
                v2_error=exc,
            )

    @endpoint('file.edit')
    def edit(self, *, file_name: object | None, item_id: int) -> object | None:
        body = compact_dict({
            'fileName': map_enum('fileName', file_name),
        })
        return require_response_body(self.session.put(f'/files/{item_id}', body=body), endpoint_id='file.edit', feature='附件编辑')

    @endpoint('file.delete')
    def delete(self, *, item_id: int) -> object | None:
        return require_response_body(
            self.session.delete(f'/files/{item_id}'),
            endpoint_id='file.delete',
            feature='附件删除',
        )

    @staticmethod
    def _is_empty_v2_upload(error: ApiError) -> bool:
        return (
            error.details.get('method') == 'POST'
            and error.details.get('path') == '/files'
            and error.details.get('response') is None
        )

    def _upload_bug_through_legacy_form(
        self,
        *,
        file_path: Path,
        bug_id: object | None,
        v2_error: ApiError,
    ) -> object:
        if not isinstance(bug_id, int) or isinstance(bug_id, bool) or bug_id <= 0:
            raise v2_error
        if not file_path.is_file():
            raise v2_error

        # The v2 write has an unknown application result when its body is
        # empty. Read the object before considering the compatibility write;
        # an exact attachment match means the first request already persisted
        # and must not be submitted again.
        after_v2 = self._read_bug_detail(bug_id, v2_error, file_path=file_path, stage='v2_readback')
        matched = self._find_attachment(after_v2, file_path.name, file_path.stat().st_size)
        if matched is not None:
            return matched

        fields = self._legacy_bug_fields(after_v2, bug_id)
        config = getattr(self.session, 'config', None)
        base_url = getattr(config, 'base_url', None)
        account = getattr(config, 'account', None)
        password = getattr(config, 'password', None)
        if not all(isinstance(value, str) and value for value in (base_url, account, password)):
            raise ApiError(
                'file.upload 返回空响应，且无法安全建立页面兼容上传会话',
                self._fallback_details(v2_error, file_path, bug_id, stage='config'),
            ) from v2_error

        client = LegacyWebClient(base_url=base_url, account=account, password=password)
        try:
            client.upload_bug_attachment(bug_id=bug_id, fields=fields, file=file_path)
        except LegacyPageFailure as exc:
            if exc.stage == 'upload':
                verified = self._read_after_legacy_write(bug_id, file_path, exc, v2_error)
                if verified is not None:
                    return verified
                if exc.transport_uncertain:
                    raise UnknownWriteResult('页面附件上传结果未知，已完成一次只读回读且未确认落库') from exc
            raise ApiError(
                'ZenTao 页面表单上传失败，未再次重试',
                self._fallback_details(v2_error, file_path, bug_id, stage=exc.stage, status=exc.status),
            ) from exc

        try:
            after_page = self._read_bug_detail(bug_id, v2_error, file_path=file_path, stage='legacy_readback')
        except Exception as exc:
            raise UnknownWriteResult('页面附件上传已提交，但无法完成回读确认') from exc
        matched = self._find_attachment(after_page, file_path.name, file_path.stat().st_size)
        if matched is None:
            raise ApiError(
                '页面表单返回成功但回读未发现附件，未再次重试',
                self._fallback_details(v2_error, file_path, bug_id, stage='legacy_readback'),
            )
        return matched

    def _read_after_legacy_write(
        self,
        bug_id: int,
        file_path: Path,
        page_error: LegacyPageFailure,
        v2_error: ApiError,
    ) -> object | None:
        try:
            detail = self._read_bug_detail(bug_id, v2_error, file_path=file_path, stage='legacy_error_readback')
        except Exception:
            if page_error.transport_uncertain:
                raise UnknownWriteResult('页面附件上传结果未知，回读也未完成') from page_error
            raise ApiError(
                '页面附件上传返回错误，且回读未完成，未再次重试',
                self._fallback_details(v2_error, file_path, bug_id, stage='legacy_error_readback', status=page_error.status),
            ) from page_error
        return self._find_attachment(detail, file_path.name, file_path.stat().st_size)

    def _read_bug_detail(
        self,
        bug_id: int,
        v2_error: ApiError,
        *,
        file_path: Path | None = None,
        stage: str,
    ) -> dict[str, Any]:
        detail_path = file_path or Path('upload')
        try:
            result = self._bugs.view(item_id=bug_id)
        except Exception as exc:
            raise ApiError(
                'file.upload 返回空响应，但无法通过 Bug 详情确认附件是否落库',
                self._fallback_details(v2_error, detail_path, bug_id, stage=stage),
            ) from exc
        if not isinstance(result, dict):
            raise ApiError(
                'Bug 详情响应不是对象，无法确认附件是否落库',
                self._fallback_details(v2_error, detail_path, bug_id, stage=stage),
            )
        bug = result.get('bug')
        if isinstance(bug, dict):
            return bug
        if result.get('id') is not None:
            return result
        raise ApiError(
            'Bug 详情响应缺少 bug 对象，无法确认附件是否落库',
            self._fallback_details(v2_error, detail_path, bug_id, stage=stage),
        )

    @staticmethod
    def _find_attachment(detail: dict[str, Any], file_name: str, file_size: int) -> dict[str, Any] | None:
        files = detail.get('files')
        entries: list[object]
        if isinstance(files, dict):
            entries = list(files.values())
        elif isinstance(files, list):
            entries = files
        else:
            entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = next((entry.get(key) for key in ('title', 'name', 'fileName', 'filename') if entry.get(key)), None)
            if name != file_name:
                continue
            raw_size = entry.get('size')
            if raw_size is not None:
                try:
                    if int(raw_size) != file_size:
                        continue
                except (TypeError, ValueError):
                    continue
            if entry.get('id') is None:
                continue
            return dict(entry)
        return None

    @classmethod
    def _legacy_bug_fields(cls, bug: dict[str, Any], bug_id: int) -> list[tuple[str, object]]:
        title = bug.get('title')
        opened_build = cls._form_values(bug.get('openedBuild'))
        if not isinstance(title, str) or not title.strip() or not opened_build:
            raise ApiError(
                'Bug 当前详情缺少页面编辑所需的 title 或 openedBuild，未执行兼容上传',
                {'object_type': 'bug', 'object_id': bug_id, 'required': ['title', 'openedBuild']},
            )

        fields: list[tuple[str, object]] = [
            ('id', bug_id),
            ('title', title),
            ('uid', uuid.uuid4().hex),
        ]
        scalar_fields = (
            'product', 'branch', 'module', 'project', 'execution', 'plan', 'story', 'task',
            'case', 'testtask', 'severity', 'pri', 'type', 'steps', 'status', 'resolution',
            'resolvedBuild', 'assignedTo', 'feedbackBy', 'notifyEmail', 'keywords', 'deadline',
            'resolvedDate', 'closedDate', 'duplicateBug', 'color',
        )
        for name in scalar_fields:
            value = bug.get(name)
            if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                fields.append((name, value))
        for name in ('os', 'browser', 'mailto', 'relatedBug'):
            for value in cls._form_values(bug.get(name)):
                fields.append((f'{name}[]', value))
        for value in opened_build:
            fields.append(('openedBuild[]', value))
        # Do not carry a stale optimistic-concurrency timestamp from the API
        # response into the HTML form. ZenTao accepts an empty value here and
        # the page request is otherwise a field-preserving edit.
        fields.append(('lastEditedDate', ''))
        return fields

    @staticmethod
    def _form_values(value: object) -> list[str]:
        if isinstance(value, (list, tuple)):
            values = value
        elif isinstance(value, str):
            values = value.split(',') if ',' in value else [value]
        else:
            values = []
        return [str(item).strip() for item in values if str(item).strip()]

    @staticmethod
    def _fallback_details(
        v2_error: ApiError,
        file_path: Path,
        bug_id: int,
        *,
        stage: str,
        status: int | None = None,
    ) -> dict[str, object]:
        details: dict[str, object] = {
            'object_type': 'bug',
            'object_id': bug_id,
            'file_name': file_path.name,
            'stage': stage,
            'v2_error': v2_error.code,
        }
        if status is not None:
            details['status'] = status
        return details
