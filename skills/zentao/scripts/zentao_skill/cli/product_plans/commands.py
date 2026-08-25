from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.product_plans.service import ProductPlansService
from ..common import add_json_flag, auto_value, non_negative_int, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'product-plan.delete', 'product-plan.edit', 'product-plan.list_product', 'product-plan.create', 'product-plan.view'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建产品计划')
    p_create.add_argument('--product', type=positive_int, required=True, dest='product', help='product 参数')
    p_create.add_argument('--title', type=str, required=True, dest='title', help='title 参数')
    p_create.add_argument('--parent', type=non_negative_int, dest='parent', help='parent 参数')
    p_create.add_argument('--begin', type=str, dest='begin', help='begin 参数')
    p_create.add_argument('--end', type=str, dest='end', help='end 参数')
    p_create.add_argument('--branch', type=non_negative_int, dest='branch', help='branch 参数')
    p_create_g_desc = p_create.add_mutually_exclusive_group(required=False)
    p_create_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_create_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改产品计划')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--product', type=positive_int, required=True, dest='product', help='product 参数；用于保留计划归属')
    p_edit.add_argument('--status', choices=['wait', 'doing', 'done', 'closed'], required=True, dest='status', help='status 参数；用于保留计划状态')
    p_edit.add_argument('--title', type=str, required=True, dest='title', help='title 参数')
    p_edit.add_argument('--parent', type=non_negative_int, dest='parent', help='parent 参数')
    p_edit.add_argument('--begin', type=str, dest='begin', help='begin 参数')
    p_edit.add_argument('--end', type=str, dest='end', help='end 参数')
    p_edit.add_argument('--branch', type=non_negative_int, dest='branch', help='branch 参数')
    p_edit_g_desc = p_edit.add_mutually_exclusive_group(required=False)
    p_edit_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_edit_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取产品计划列表')
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
    p_view = resource_subparsers.add_parser('view', help='获取产品计划详情')
    p_view.add_argument("id", type=positive_int, help="资源 ID")
    add_json_flag(p_view)
    p_view.set_defaults(_handler=_run_view)
    p_delete = resource_subparsers.add_parser('delete', help='删除产品计划')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: ProductPlansService = getattr(services, 'product_plan')
    return service.create(product=getattr(args, 'product', None), title=getattr(args, 'title', None), parent=getattr(args, 'parent', None), begin=getattr(args, 'begin', None), end=getattr(args, 'end', None), branch=getattr(args, 'branch', None), desc=resolve_text(args, 'desc'))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: ProductPlansService = getattr(services, 'product_plan')
    return service.edit(item_id=args.id, product=getattr(args, 'product', None), status=getattr(args, 'status', None), title=getattr(args, 'title', None), parent=getattr(args, 'parent', None), begin=getattr(args, 'begin', None), end=getattr(args, 'end', None), branch=getattr(args, 'branch', None), desc=resolve_text(args, 'desc'))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: ProductPlansService = getattr(services, 'product_plan')
    if getattr(args, 'product', None) is not None:
        return service.list_product(product=getattr(args, 'product'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    raise UsageError("必须选择一个列表 scope")

def _run_view(services: object, args: argparse.Namespace) -> object | None:
    service: ProductPlansService = getattr(services, 'product_plan')
    return service.view(item_id=args.id)

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: ProductPlansService = getattr(services, 'product_plan')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
