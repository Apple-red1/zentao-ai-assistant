from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.products.service import ProductsService
from ..common import add_json_flag, auto_value, non_negative_int, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'product.delete', 'product.edit', 'product.list_program', 'product.view', 'product.create', 'product.list'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建产品')
    p_create.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_create.add_argument('--program', type=positive_int, dest='program', help='program 参数')
    p_create.add_argument('--line', type=non_negative_int, dest='line', help='line 参数；允许 0 表示无产品线')
    p_create.add_argument('--type', type=str, choices=['branch', 'normal', 'platform'], dest='type', help='type 参数')
    p_create.add_argument('--po', type=str, dest='po', help='po 参数')
    p_create.add_argument('--reviewer', action='append', dest='reviewer', help='reviewer 参数')
    p_create.add_argument('--desc', action='append', dest='desc', help='desc 参数')
    p_create.add_argument('--qd', type=str, dest='qd', help='qd 参数')
    p_create.add_argument('--rd', type=str, dest='rd', help='rd 参数')
    p_create.add_argument('--acl', type=str, choices=['open', 'private'], dest='acl', help='acl 参数')
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改产品')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_edit.add_argument('--program', type=positive_int, dest='program', help='program 参数')
    p_edit.add_argument('--line', type=non_negative_int, dest='line', help='line 参数；允许 0 表示无产品线')
    p_edit.add_argument('--type', type=str, choices=['branch', 'normal', 'platform'], dest='type', help='type 参数')
    p_edit.add_argument('--po', type=str, dest='po', help='po 参数')
    p_edit.add_argument('--reviewer', action='append', dest='reviewer', help='reviewer 参数')
    p_edit.add_argument('--desc', action='append', dest='desc', help='desc 参数')
    p_edit.add_argument('--qd', type=str, dest='qd', help='qd 参数')
    p_edit.add_argument('--rd', type=str, dest='rd', help='rd 参数')
    p_edit.add_argument('--acl', type=str, choices=['open', 'private'], dest='acl', help='acl 参数')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取产品列表')
    p_list_scope = p_list.add_mutually_exclusive_group(required=False)
    p_list_scope.add_argument("--program", type=positive_int, dest='program', help='program scope ID')
    p_list.add_argument('--browse', type=str, dest='browse', help='browse 参数')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)
    p_view = resource_subparsers.add_parser('view', help='获取产品详情')
    p_view.add_argument("id", type=positive_int, help="资源 ID")
    add_json_flag(p_view)
    p_view.set_defaults(_handler=_run_view)
    p_delete = resource_subparsers.add_parser('delete', help='删除产品')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: ProductsService = getattr(services, 'product')
    value_type = getattr(args, 'type', None)
    if value_type is not None and value_type not in {'branch', 'platform', 'normal'}:
        raise UsageError("--type 不是当前 endpoint 支持的枚举值")
    value_acl = getattr(args, 'acl', None)
    if value_acl is not None and value_acl not in {'open', 'private'}:
        raise UsageError("--acl 不是当前 endpoint 支持的枚举值")
    return service.create(name=getattr(args, 'name', None), program=getattr(args, 'program', None), line=getattr(args, 'line', None), type=getattr(args, 'type', None), po=getattr(args, 'po', None), reviewer=getattr(args, 'reviewer', None), desc=getattr(args, 'desc', None), qd=getattr(args, 'qd', None), rd=getattr(args, 'rd', None), acl=getattr(args, 'acl', None))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: ProductsService = getattr(services, 'product')
    value_type = getattr(args, 'type', None)
    if value_type is not None and value_type not in {'branch', 'platform', 'normal'}:
        raise UsageError("--type 不是当前 endpoint 支持的枚举值")
    value_acl = getattr(args, 'acl', None)
    if value_acl is not None and value_acl not in {'open', 'private'}:
        raise UsageError("--acl 不是当前 endpoint 支持的枚举值")
    return service.edit(item_id=args.id, name=getattr(args, 'name', None), program=getattr(args, 'program', None), line=getattr(args, 'line', None), type=getattr(args, 'type', None), po=getattr(args, 'po', None), reviewer=getattr(args, 'reviewer', None), desc=getattr(args, 'desc', None), qd=getattr(args, 'qd', None), rd=getattr(args, 'rd', None), acl=getattr(args, 'acl', None))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: ProductsService = getattr(services, 'product')
    if getattr(args, 'program', None) is not None:
        return service.list_program(program=getattr(args, 'program'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None))
    else:
        return service.list(browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None))

def _run_view(services: object, args: argparse.Namespace) -> object | None:
    service: ProductsService = getattr(services, 'product')
    return service.view(item_id=args.id)

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: ProductsService = getattr(services, 'product')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
