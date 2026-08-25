from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.systems.service import SystemsService
from ..common import add_json_flag, auto_value, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'system.list_product', 'system.edit', 'system.create'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建应用')
    p_create.add_argument('--product', type=positive_int, required=True, dest='product', help='product 参数')
    p_create.add_argument('--integrated', type=positive_int, required=True, dest='integrated', help='integrated 参数')
    p_create.add_argument('--child', action='append', required=True, dest='child', help='child 参数')
    p_create.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_create_g_desc = p_create.add_mutually_exclusive_group(required=False)
    p_create_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_create_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改应用')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_edit.add_argument('--child', action='append', required=True, dest='child', help='child 参数')
    p_edit_g_desc = p_edit.add_mutually_exclusive_group(required=False)
    p_edit_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_edit_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取产品应用列表')
    p_list_scope = p_list.add_mutually_exclusive_group(required=True)
    p_list_scope.add_argument("--product", type=positive_int, dest='product', help='product scope ID')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: SystemsService = getattr(services, 'system')
    return service.create(product=getattr(args, 'product', None), integrated=getattr(args, 'integrated', None), child=getattr(args, 'child', None), name=getattr(args, 'name', None), desc=resolve_text(args, 'desc'))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: SystemsService = getattr(services, 'system')
    return service.edit(item_id=args.id, name=getattr(args, 'name', None), child=getattr(args, 'child', None), desc=resolve_text(args, 'desc'))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: SystemsService = getattr(services, 'system')
    if getattr(args, 'product', None) is not None:
        return service.list_product(product=getattr(args, 'product'), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None))
    raise UsageError("必须选择一个列表 scope")
