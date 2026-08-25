from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.test_tasks.service import TestTasksService
from ..common import add_json_flag, auto_value, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'test-task.delete', 'test-task.edit', 'test-task.list_product', 'test-task.list_project', 'test-task.create', 'test-task.list_execution'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建测试单')
    p_create.add_argument('--product', type=positive_int, required=True, dest='product', help='product 参数')
    p_create.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_create.add_argument('--build', type=positive_int, required=True, dest='build', help='build 参数')
    p_create.add_argument('--execution', type=positive_int, dest='execution', help='execution 参数')
    p_create.add_argument('--type', action='append', choices=['acceptance', 'integrate', 'performance', 'safety', 'system'], dest='type', help='type 参数')
    p_create.add_argument('--owner', type=str, dest='owner', help='owner 参数')
    p_create.add_argument('--status', type=str, choices=['blocked', 'doing', 'done', 'wait'], dest='status', help='status 参数')
    p_create.add_argument('--begin', type=str, required=True, dest='begin', help='begin 参数')
    p_create.add_argument('--end', type=str, required=True, dest='end', help='end 参数')
    p_create_g_desc = p_create.add_mutually_exclusive_group(required=False)
    p_create_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_create_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改测试单')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_edit.add_argument('--build', type=positive_int, required=True, dest='build', help='build 参数')
    p_edit.add_argument('--execution', type=positive_int, dest='execution', help='execution 参数')
    p_edit.add_argument('--type', action='append', choices=['acceptance', 'integrate', 'performance', 'safety', 'system'], dest='type', help='type 参数')
    p_edit.add_argument('--owner', type=str, dest='owner', help='owner 参数')
    p_edit.add_argument('--status', type=str, choices=['blocked', 'doing', 'done', 'wait'], dest='status', help='status 参数')
    p_edit.add_argument('--begin', type=str, required=True, dest='begin', help='begin 参数')
    p_edit.add_argument('--end', type=str, required=True, dest='end', help='end 参数')
    p_edit_g_desc = p_edit.add_mutually_exclusive_group(required=False)
    p_edit_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_edit_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取产品测试单列表')
    p_list_scope = p_list.add_mutually_exclusive_group(required=True)
    p_list_scope.add_argument("--product", type=positive_int, dest='product', help='product scope ID')
    p_list_scope.add_argument("--project", type=positive_int, dest='project', help='project scope ID')
    p_list_scope.add_argument("--execution", type=positive_int, dest='execution', help='execution scope ID')
    p_list.add_argument('--browse', type=str, dest='browse', help='browse 参数')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)
    p_delete = resource_subparsers.add_parser('delete', help='删除测试单')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: TestTasksService = getattr(services, 'test_task')
    value_type = getattr(args, 'type', None)
    if value_type is not None and any(v not in {'integrate', 'safety', 'performance', 'system', 'acceptance'} for v in value_type):
        raise UsageError("--type 包含当前 endpoint 不支持的枚举值")
    value_status = getattr(args, 'status', None)
    if value_status is not None and value_status not in {'done', 'wait', 'blocked', 'doing'}:
        raise UsageError("--status 不是当前 endpoint 支持的枚举值")
    return service.create(product=getattr(args, 'product', None), name=getattr(args, 'name', None), build=getattr(args, 'build', None), execution=getattr(args, 'execution', None), type=getattr(args, 'type', None), owner=getattr(args, 'owner', None), status=getattr(args, 'status', None), begin=getattr(args, 'begin', None), end=getattr(args, 'end', None), desc=resolve_text(args, 'desc'))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: TestTasksService = getattr(services, 'test_task')
    value_type = getattr(args, 'type', None)
    if value_type is not None and any(v not in {'integrate', 'safety', 'performance', 'system', 'acceptance'} for v in value_type):
        raise UsageError("--type 包含当前 endpoint 不支持的枚举值")
    value_status = getattr(args, 'status', None)
    if value_status is not None and value_status not in {'done', 'wait', 'blocked', 'doing'}:
        raise UsageError("--status 不是当前 endpoint 支持的枚举值")
    return service.edit(item_id=args.id, name=getattr(args, 'name', None), build=getattr(args, 'build', None), execution=getattr(args, 'execution', None), type=getattr(args, 'type', None), owner=getattr(args, 'owner', None), status=getattr(args, 'status', None), begin=getattr(args, 'begin', None), end=getattr(args, 'end', None), desc=resolve_text(args, 'desc'))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: TestTasksService = getattr(services, 'test_task')
    if getattr(args, 'product', None) is not None:
        return service.list_product(product=getattr(args, 'product'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None))
    elif getattr(args, 'project', None) is not None:
        return service.list_project(project=getattr(args, 'project'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None))
    elif getattr(args, 'execution', None) is not None:
        return service.list_execution(execution=getattr(args, 'execution'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None))
    raise UsageError("必须选择一个列表 scope")

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: TestTasksService = getattr(services, 'test_task')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
