from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.test_cases.service import TestCasesService
from ..common import add_json_flag, auto_value, non_negative_int, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'test-case.list_project', 'test-case.view', 'test-case.delete', 'test-case.list_execution', 'test-case.list_product', 'test-case.create', 'test-case.edit'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建测试用例')
    p_create.add_argument('--product', type=positive_int, required=True, dest='product', help='product 参数')
    p_create.add_argument('--title', type=str, required=True, dest='title', help='title 参数')
    p_create.add_argument('--module', type=non_negative_int, dest='module', help='module 参数；允许 0 表示根模块')
    p_create.add_argument('--story', type=positive_int, dest='story', help='story 参数')
    p_create.add_argument('--priority', type=positive_int, dest='priority', help='priority 参数')
    p_create.add_argument('--type', type=str, choices=['config', 'feature', 'install', 'interface', 'other', 'performance', 'security', 'unit'], dest='type', help='type 参数')
    p_create_g_precondition = p_create.add_mutually_exclusive_group(required=False)
    p_create_g_precondition.add_argument('--precondition', dest='precondition', type=str, help='precondition 参数')
    p_create_g_precondition.add_argument('--precondition-file', dest='precondition_file', help="从 UTF-8 文件读取文本")
    p_create.add_argument('--step', action='append', dest='step', help='step 参数')
    p_create.add_argument('--expect', action='append', dest='expect', help='expect 参数')
    p_create.add_argument('--step-type', action='append', choices=['group', 'step'], dest='step_type', help='step-type 参数')
    p_create.add_argument('--project', type=positive_int, dest='project', help='project 参数')
    p_create.add_argument('--execution', type=positive_int, dest='execution', help='execution 参数')
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改测试用例')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--title', type=str, required=True, dest='title', help='title 参数')
    p_edit.add_argument('--module', type=non_negative_int, dest='module', help='module 参数；允许 0 表示根模块')
    p_edit.add_argument('--story', type=positive_int, dest='story', help='story 参数')
    p_edit.add_argument('--priority', type=positive_int, dest='priority', help='priority 参数')
    p_edit.add_argument('--type', type=str, choices=['config', 'feature', 'install', 'interface', 'other', 'performance', 'security', 'unit'], dest='type', help='type 参数')
    p_edit_g_precondition = p_edit.add_mutually_exclusive_group(required=False)
    p_edit_g_precondition.add_argument('--precondition', dest='precondition', type=str, help='precondition 参数')
    p_edit_g_precondition.add_argument('--precondition-file', dest='precondition_file', help="从 UTF-8 文件读取文本")
    p_edit.add_argument('--step', action='append', dest='step', help='step 参数')
    p_edit.add_argument('--expect', action='append', dest='expect', help='expect 参数')
    p_edit.add_argument('--step-type', action='append', choices=['group', 'step'], dest='step_type', help='step-type 参数')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取产品测试用例列表')
    p_list_scope = p_list.add_mutually_exclusive_group(required=True)
    p_list_scope.add_argument("--product", type=positive_int, dest='product', help='product scope ID')
    p_list_scope.add_argument("--project", type=positive_int, dest='project', help='project scope ID')
    p_list_scope.add_argument("--execution", type=positive_int, dest='execution', help='execution scope ID')
    p_list.add_argument('--browse', type=str, dest='browse', help='browse 参数')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    p_list.add_argument('--filters', type=str, dest='filters', help='filters 参数')
    p_list.add_argument('--group-join', type=str, dest='group_join', help='group-join 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)
    p_view = resource_subparsers.add_parser('view', help='获取测试用例详情')
    p_view.add_argument("id", type=positive_int, help="资源 ID")
    add_json_flag(p_view)
    p_view.set_defaults(_handler=_run_view)
    p_delete = resource_subparsers.add_parser('delete', help='删除测试用例')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: TestCasesService = getattr(services, 'test_case')
    value_type = getattr(args, 'type', None)
    if value_type is not None and value_type not in {'interface', 'unit', 'performance', 'config', 'other', 'feature', 'security', 'install'}:
        raise UsageError("--type 不是当前 endpoint 支持的枚举值")
    value_step_type = getattr(args, 'step_type', None)
    if value_step_type is not None and any(v not in {'group', 'step'} for v in value_step_type):
        raise UsageError("--step-type 包含当前 endpoint 不支持的枚举值")
    return service.create(product=getattr(args, 'product', None), title=getattr(args, 'title', None), module=getattr(args, 'module', None), story=getattr(args, 'story', None), priority=getattr(args, 'priority', None), type=getattr(args, 'type', None), precondition=resolve_text(args, 'precondition'), step=getattr(args, 'step', None), expect=getattr(args, 'expect', None), step_type=getattr(args, 'step_type', None), project=getattr(args, 'project', None), execution=getattr(args, 'execution', None))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: TestCasesService = getattr(services, 'test_case')
    value_type = getattr(args, 'type', None)
    if value_type is not None and value_type not in {'interface', 'unit', 'performance', 'config', 'other', 'feature', 'security', 'install'}:
        raise UsageError("--type 不是当前 endpoint 支持的枚举值")
    value_step_type = getattr(args, 'step_type', None)
    if value_step_type is not None and any(v not in {'group', 'step'} for v in value_step_type):
        raise UsageError("--step-type 包含当前 endpoint 不支持的枚举值")
    return service.edit(item_id=args.id, title=getattr(args, 'title', None), module=getattr(args, 'module', None), story=getattr(args, 'story', None), priority=getattr(args, 'priority', None), type=getattr(args, 'type', None), precondition=resolve_text(args, 'precondition'), step=getattr(args, 'step', None), expect=getattr(args, 'expect', None), step_type=getattr(args, 'step_type', None))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: TestCasesService = getattr(services, 'test_case')
    if getattr(args, 'product', None) is not None:
        return service.list_product(product=getattr(args, 'product'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    elif getattr(args, 'project', None) is not None:
        return service.list_project(project=getattr(args, 'project'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    elif getattr(args, 'execution', None) is not None:
        return service.list_execution(execution=getattr(args, 'execution'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    raise UsageError("必须选择一个列表 scope")

def _run_view(services: object, args: argparse.Namespace) -> object | None:
    service: TestCasesService = getattr(services, 'test_case')
    return service.view(item_id=args.id)

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: TestCasesService = getattr(services, 'test_case')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
