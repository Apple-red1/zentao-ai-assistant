from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.tickets.service import TicketsService
from ..common import add_json_flag, auto_value, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'ticket.close', 'ticket.view', 'ticket.delete', 'ticket.create', 'ticket.activate', 'ticket.list_product', 'ticket.edit'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建工单')
    p_create.add_argument('--product', type=positive_int, required=True, dest='product', help='product 参数')
    p_create.add_argument('--module', type=positive_int, dest='module', help='module 参数')
    p_create.add_argument('--title', type=str, required=True, dest='title', help='title 参数')
    p_create.add_argument('--type', type=str, choices=['affair', 'code', 'data', 'security', 'stuck'], dest='type', help='type 参数')
    p_create_g_desc = p_create.add_mutually_exclusive_group(required=False)
    p_create_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_create_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    p_create.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_create.add_argument('--deadline', type=str, dest='deadline', help='deadline 参数')
    p_create.add_argument('--affected-build', action='append', dest='affected_build', help='affected-build 参数')
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改工单')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--product', type=positive_int, dest='product', help='product 参数')
    p_edit.add_argument('--module', type=positive_int, dest='module', help='module 参数')
    p_edit.add_argument('--title', type=str, dest='title', help='title 参数')
    p_edit.add_argument('--type', type=str, choices=['affair', 'code', 'data', 'security', 'stuck'], dest='type', help='type 参数')
    p_edit_g_desc = p_edit.add_mutually_exclusive_group(required=False)
    p_edit_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_edit_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    p_edit.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_edit.add_argument('--deadline', type=str, dest='deadline', help='deadline 参数')
    p_edit.add_argument('--affected-build', action='append', dest='affected_build', help='affected-build 参数')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取产品工单列表')
    p_list_scope = p_list.add_mutually_exclusive_group(required=True)
    p_list_scope.add_argument("--product", type=positive_int, dest='product', help='product scope ID')
    p_list.add_argument('--browse', type=str, dest='browse', help='browse 参数')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    p_list.add_argument('--filters', type=str, dest='filters', help='filters 参数')
    p_list.add_argument('--group-join', type=str, dest='group_join', help='group-join 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)
    p_view = resource_subparsers.add_parser('view', help='获取工单详情')
    p_view.add_argument("id", type=positive_int, help="资源 ID")
    add_json_flag(p_view)
    p_view.set_defaults(_handler=_run_view)
    p_close = resource_subparsers.add_parser('close', help='关闭工单')
    p_close.add_argument("id", type=positive_int, help="资源 ID")
    p_close.add_argument('--closed-reason', type=str, required=True, choices=['commented', 'refuse', 'repeat'], dest='closed_reason', help='closed-reason 参数')
    p_close_g_comment = p_close.add_mutually_exclusive_group(required=True)
    p_close_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_close_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_close)
    p_close.set_defaults(_handler=_run_close)
    p_activate = resource_subparsers.add_parser('activate', help='激活工单')
    p_activate.add_argument("id", type=positive_int, help="资源 ID")
    p_activate.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_activate_g_comment = p_activate.add_mutually_exclusive_group(required=False)
    p_activate_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_activate_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_activate)
    p_activate.set_defaults(_handler=_run_activate)
    p_delete = resource_subparsers.add_parser('delete', help='删除工单')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: TicketsService = getattr(services, 'ticket')
    value_type = getattr(args, 'type', None)
    if value_type is not None and value_type not in {'data', 'stuck', 'security', 'affair', 'code'}:
        raise UsageError("--type 不是当前 endpoint 支持的枚举值")
    return service.create(product=getattr(args, 'product', None), module=getattr(args, 'module', None), title=getattr(args, 'title', None), type=getattr(args, 'type', None), desc=resolve_text(args, 'desc'), assignee=getattr(args, 'assignee', None), deadline=getattr(args, 'deadline', None), affected_build=getattr(args, 'affected_build', None))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: TicketsService = getattr(services, 'ticket')
    value_type = getattr(args, 'type', None)
    if value_type is not None and value_type not in {'data', 'stuck', 'security', 'affair', 'code'}:
        raise UsageError("--type 不是当前 endpoint 支持的枚举值")
    return service.edit(item_id=args.id, product=getattr(args, 'product', None), module=getattr(args, 'module', None), title=getattr(args, 'title', None), type=getattr(args, 'type', None), desc=resolve_text(args, 'desc'), assignee=getattr(args, 'assignee', None), deadline=getattr(args, 'deadline', None), affected_build=getattr(args, 'affected_build', None))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: TicketsService = getattr(services, 'ticket')
    if getattr(args, 'product', None) is not None:
        return service.list_product(product=getattr(args, 'product'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    raise UsageError("必须选择一个列表 scope")

def _run_view(services: object, args: argparse.Namespace) -> object | None:
    service: TicketsService = getattr(services, 'ticket')
    return service.view(item_id=args.id)

def _run_close(services: object, args: argparse.Namespace) -> object | None:
    service: TicketsService = getattr(services, 'ticket')
    value_closed_reason = getattr(args, 'closed_reason', None)
    if value_closed_reason is not None and value_closed_reason not in {'repeat', 'refuse', 'commented'}:
        raise UsageError("--closed-reason 不是当前 endpoint 支持的枚举值")
    return service.close(item_id=args.id, closed_reason=getattr(args, 'closed_reason', None), comment=resolve_text(args, 'comment'))

def _run_activate(services: object, args: argparse.Namespace) -> object | None:
    service: TicketsService = getattr(services, 'ticket')
    return service.activate(item_id=args.id, assignee=getattr(args, 'assignee', None), comment=resolve_text(args, 'comment'))

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: TicketsService = getattr(services, 'ticket')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
