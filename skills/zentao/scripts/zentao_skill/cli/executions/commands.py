from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.executions.service import ExecutionsService
from ..common import add_json_flag, auto_value, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'execution.edit', 'execution.view', 'execution.list', 'execution.list_project', 'execution.create', 'execution.delete'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建执行')
    p_create.add_argument('--project', type=positive_int, required=True, dest='project', help='project 参数')
    p_create.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_create.add_argument('--type', type=str, choices=['kanban', 'sprint', 'stage'], dest='type', help='type 参数')
    p_create.add_argument('--parent', type=positive_int, dest='parent', help='parent 参数')
    p_create.add_argument('--attribute', type=str, choices=['concept', 'design', 'dev', 'develop', 'launch', 'mix', 'other', 'plan', 'qa', 'qualify', 'release', 'request', 'review'], dest='attribute', help='attribute 参数')
    p_create.add_argument('--lifetime', type=str, choices=['long', 'ops', 'short'], dest='lifetime', help='lifetime 参数')
    p_create.add_argument('--begin', type=str, required=True, dest='begin', help='begin 参数')
    p_create.add_argument('--end', type=str, required=True, dest='end', help='end 参数')
    p_create.add_argument('--days', type=positive_int, dest='days', help='days 参数')
    p_create.add_argument('--product', action='append', required=True, dest='product', help='product 参数')
    p_create.add_argument('--plan', action='append', dest='plan', help='plan 参数')
    p_create.add_argument('--po', type=str, dest='po', help='po 参数')
    p_create.add_argument('--qd', type=str, dest='qd', help='qd 参数')
    p_create.add_argument('--pm', type=str, dest='pm', help='pm 参数')
    p_create.add_argument('--rd', type=str, dest='rd', help='rd 参数')
    p_create.add_argument('--acl', type=str, choices=['open', 'private'], dest='acl', help='acl 参数')
    p_create.add_argument('--milestone', type=positive_int, dest='milestone', help='milestone 参数')
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改执行')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_edit.add_argument('--begin', type=str, required=True, dest='begin', help='begin 参数')
    p_edit.add_argument('--end', type=str, required=True, dest='end', help='end 参数')
    p_edit.add_argument('--project', type=positive_int, dest='project', help='project 参数')
    p_edit.add_argument('--lifetime', type=str, dest='lifetime', help='lifetime 参数')
    p_edit.add_argument('--days', type=positive_int, dest='days', help='days 参数')
    p_edit.add_argument('--product', action='append', dest='product', help='product 参数')
    p_edit.add_argument('--plan', action='append', dest='plan', help='plan 参数')
    p_edit.add_argument('--po', type=str, dest='po', help='po 参数')
    p_edit.add_argument('--qd', type=str, dest='qd', help='qd 参数')
    p_edit.add_argument('--pm', type=str, dest='pm', help='pm 参数')
    p_edit.add_argument('--rd', type=str, dest='rd', help='rd 参数')
    p_edit.add_argument('--acl', type=str, dest='acl', help='acl 参数')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取执行列表')
    p_list_scope = p_list.add_mutually_exclusive_group(required=False)
    p_list_scope.add_argument("--project", type=positive_int, dest='project', help='project scope ID')
    p_list.add_argument('--browse', type=str, dest='browse', help='browse 参数')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    p_list.add_argument('--filters', type=str, dest='filters', help='filters 参数')
    p_list.add_argument('--group-join', type=str, dest='group_join', help='group-join 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)
    p_view = resource_subparsers.add_parser('view', help='获取执行详情')
    p_view.add_argument("id", type=positive_int, help="资源 ID")
    add_json_flag(p_view)
    p_view.set_defaults(_handler=_run_view)
    p_delete = resource_subparsers.add_parser('delete', help='删除执行')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: ExecutionsService = getattr(services, 'execution')
    value_type = getattr(args, 'type', None)
    if value_type is not None and value_type not in {'sprint', 'stage', 'kanban'}:
        raise UsageError("--type 不是当前 endpoint 支持的枚举值")
    value_attribute = getattr(args, 'attribute', None)
    if value_attribute is not None and value_attribute not in {'design', 'dev', 'develop', 'launch', 'concept', 'other', 'request', 'review', 'plan', 'mix', 'qualify', 'release', 'qa'}:
        raise UsageError("--attribute 不是当前 endpoint 支持的枚举值")
    value_lifetime = getattr(args, 'lifetime', None)
    if value_lifetime is not None and value_lifetime not in {'ops', 'short', 'long'}:
        raise UsageError("--lifetime 不是当前 endpoint 支持的枚举值")
    value_acl = getattr(args, 'acl', None)
    if value_acl is not None and value_acl not in {'open', 'private'}:
        raise UsageError("--acl 不是当前 endpoint 支持的枚举值")
    return service.create(project=getattr(args, 'project', None), name=getattr(args, 'name', None), type=getattr(args, 'type', None), parent=getattr(args, 'parent', None), attribute=getattr(args, 'attribute', None), lifetime=getattr(args, 'lifetime', None), begin=getattr(args, 'begin', None), end=getattr(args, 'end', None), days=getattr(args, 'days', None), product=getattr(args, 'product', None), plan=getattr(args, 'plan', None), po=getattr(args, 'po', None), qd=getattr(args, 'qd', None), pm=getattr(args, 'pm', None), rd=getattr(args, 'rd', None), acl=getattr(args, 'acl', None), milestone=getattr(args, 'milestone', None))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: ExecutionsService = getattr(services, 'execution')
    return service.edit(item_id=args.id, name=getattr(args, 'name', None), begin=getattr(args, 'begin', None), end=getattr(args, 'end', None), project=getattr(args, 'project', None), lifetime=getattr(args, 'lifetime', None), days=getattr(args, 'days', None), product=getattr(args, 'product', None), plan=getattr(args, 'plan', None), po=getattr(args, 'po', None), qd=getattr(args, 'qd', None), pm=getattr(args, 'pm', None), rd=getattr(args, 'rd', None), acl=getattr(args, 'acl', None))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: ExecutionsService = getattr(services, 'execution')
    if getattr(args, 'project', None) is not None:
        if getattr(args, 'filters', None) is not None or getattr(args, 'group_join', None) is not None:
            raise UsageError("所选 --project scope 不支持本次提供的某些列表参数")
        return service.list_project(project=getattr(args, 'project'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None))
    else:
        return service.list(browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))

def _run_view(services: object, args: argparse.Namespace) -> object | None:
    service: ExecutionsService = getattr(services, 'execution')
    return service.view(item_id=args.id)

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: ExecutionsService = getattr(services, 'execution')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
