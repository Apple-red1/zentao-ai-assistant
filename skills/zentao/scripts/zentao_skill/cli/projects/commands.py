from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.projects.service import ProjectsService
from ..common import add_json_flag, auto_value, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'project.create', 'project.delete', 'project.list', 'project.list_program', 'project.edit'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建项目')
    p_create.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_create.add_argument('--model', type=str, required=True, choices=['agile-plus', 'kanban', 'scrum', 'waterfall', 'waterfall-plus'], dest='model', help='model 参数')
    p_create.add_argument('--begin', type=str, required=True, dest='begin', help='begin 参数')
    p_create.add_argument('--end', type=str, required=True, dest='end', help='end 参数')
    p_create.add_argument('--product', action='append', dest='product', help='product 参数')
    p_create.add_argument('--parent', type=positive_int, dest='parent', help='parent 参数')
    p_create.add_argument('--workflow-group', type=positive_int, dest='workflow_group', help='workflow-group 参数')
    p_create.add_argument('--pm', type=str, dest='pm', help='pm 参数')
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改项目')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_edit.add_argument('--model', type=str, required=True, choices=['agile-plus', 'kanban', 'scrum', 'waterfall', 'waterfall-plus'], dest='model', help='model 参数')
    p_edit.add_argument('--begin', type=str, required=True, dest='begin', help='begin 参数')
    p_edit.add_argument('--end', type=str, required=True, dest='end', help='end 参数')
    p_edit.add_argument('--product', action='append', dest='product', help='product 参数')
    p_edit.add_argument('--parent', type=positive_int, dest='parent', help='parent 参数')
    p_edit.add_argument('--workflow-group', type=positive_int, dest='workflow_group', help='workflow-group 参数')
    p_edit.add_argument('--pm', type=str, dest='pm', help='pm 参数')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取项目列表')
    p_list_scope = p_list.add_mutually_exclusive_group(required=False)
    p_list_scope.add_argument("--program", type=positive_int, dest='program', help='program scope ID')
    p_list.add_argument('--browse', type=str, dest='browse', help='browse 参数')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    p_list.add_argument('--filters', type=str, dest='filters', help='filters 参数')
    p_list.add_argument('--group-join', type=str, dest='group_join', help='group-join 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)
    p_delete = resource_subparsers.add_parser('delete', help='删除项目')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: ProjectsService = getattr(services, 'project')
    value_model = getattr(args, 'model', None)
    if value_model is not None and value_model not in {'scrum', 'kanban', 'waterfall', 'agile-plus', 'waterfall-plus'}:
        raise UsageError("--model 不是当前 endpoint 支持的枚举值")
    return service.create(name=getattr(args, 'name', None), model=getattr(args, 'model', None), begin=getattr(args, 'begin', None), end=getattr(args, 'end', None), product=getattr(args, 'product', None), parent=getattr(args, 'parent', None), workflow_group=getattr(args, 'workflow_group', None), pm=getattr(args, 'pm', None))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: ProjectsService = getattr(services, 'project')
    value_model = getattr(args, 'model', None)
    if value_model is not None and value_model not in {'scrum', 'kanban', 'waterfall', 'agile-plus', 'waterfall-plus'}:
        raise UsageError("--model 不是当前 endpoint 支持的枚举值")
    return service.edit(item_id=args.id, name=getattr(args, 'name', None), model=getattr(args, 'model', None), begin=getattr(args, 'begin', None), end=getattr(args, 'end', None), product=getattr(args, 'product', None), parent=getattr(args, 'parent', None), workflow_group=getattr(args, 'workflow_group', None), pm=getattr(args, 'pm', None))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: ProjectsService = getattr(services, 'project')
    if getattr(args, 'program', None) is not None:
        if getattr(args, 'filters', None) is not None or getattr(args, 'group_join', None) is not None:
            raise UsageError("所选 --program scope 不支持本次提供的某些列表参数")
        return service.list_program(program=getattr(args, 'program'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None))
    else:
        return service.list(browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: ProjectsService = getattr(services, 'project')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
