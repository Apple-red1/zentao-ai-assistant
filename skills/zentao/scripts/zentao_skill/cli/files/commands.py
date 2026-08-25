from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.files.service import FilesService
from ..common import add_json_flag, auto_value, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'file.delete', 'file.upload', 'file.edit'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_upload = resource_subparsers.add_parser('upload', help='上传附件')
    p_upload.add_argument('--file', type=str, required=True, dest='file', help='file 参数')
    p_upload.add_argument('--object-type', type=str, required=True, choices=['bug', 'story', 'task', 'testcase'], dest='object_type', help='object-type 参数')
    p_upload.add_argument('--object-id', type=positive_int, required=True, dest='object_id', help='object-id 参数')
    add_json_flag(p_upload)
    p_upload.set_defaults(_handler=_run_upload)
    p_edit = resource_subparsers.add_parser('edit', help='修改附件名称')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--file-name', type=str, required=True, dest='file_name', help='file-name 参数')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_delete = resource_subparsers.add_parser('delete', help='删除附件')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_upload(services: object, args: argparse.Namespace) -> object | None:
    service: FilesService = getattr(services, 'file')
    value_object_type = getattr(args, 'object_type', None)
    if value_object_type is not None and value_object_type not in {'bug', 'story', 'testcase', 'task'}:
        raise UsageError("--object-type 不是当前 endpoint 支持的枚举值")
    return service.upload(file=getattr(args, 'file', None), object_type=getattr(args, 'object_type', None), object_id=getattr(args, 'object_id', None))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: FilesService = getattr(services, 'file')
    return service.edit(item_id=args.id, file_name=getattr(args, 'file_name', None))

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: FilesService = getattr(services, 'file')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
