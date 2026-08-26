from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.bugs.service import BugsService
from ..common import add_json_flag, auto_value, build_ref, non_negative_int, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'bug.create', 'bug.list_project', 'bug.activate', 'bug.delete', 'bug.edit', 'bug.list_execution', 'bug.list_product', 'bug.resolve', 'bug.close', 'bug.view'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建 Bug')
    p_create.add_argument('--product', type=positive_int, required=True, dest='product', help='product 参数')
    p_create.add_argument('--title', type=str, required=True, dest='title', help='title 参数')
    p_create.add_argument('--affected-build', action='append', required=True, dest='affected_build', help='affected-build 参数')
    p_create.add_argument('--branch', type=positive_int, dest='branch', help='branch 参数')
    p_create.add_argument('--module', type=positive_int, dest='module', help='module 参数')
    p_create.add_argument('--project', type=positive_int, dest='project', help='project 参数')
    p_create.add_argument('--execution', type=positive_int, dest='execution', help='execution 参数')
    p_create.add_argument('--story', type=non_negative_int, dest='story', help='story 参数；允许 0 表示解除关联')
    p_create.add_argument('--task', type=positive_int, dest='task', help='task 参数')
    p_create.add_argument('--severity', type=positive_int, dest='severity', help='severity 参数')
    p_create.add_argument('--priority', type=positive_int, dest='priority', help='priority 参数')
    p_create.add_argument('--type', type=str, choices=['automation', 'code-error', 'config', 'design-defect', 'install', 'others', 'performance', 'security', 'standard'], dest='type', help='type 参数')
    p_create.add_argument('--os', type=str, dest='os', help='os 参数')
    p_create.add_argument('--browser', type=str, dest='browser', help='browser 参数')
    p_create_g_steps = p_create.add_mutually_exclusive_group(required=False)
    p_create_g_steps.add_argument('--steps', dest='steps', type=str, help='steps 参数')
    p_create_g_steps.add_argument('--steps-file', dest='steps_file', help="从 UTF-8 文件读取文本")
    p_create.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_create.add_argument('--deadline', type=str, dest='deadline', help='deadline 参数')
    p_create.add_argument('--keywords', type=str, dest='keywords', help='keywords 参数')
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改 Bug')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--title', type=str, dest='title', help='title 参数')
    p_edit.add_argument('--severity', type=positive_int, dest='severity', help='severity 参数')
    p_edit.add_argument('--priority', type=positive_int, dest='priority', help='priority 参数')
    p_edit.add_argument('--type', type=str, choices=['automation', 'code-error', 'config', 'design-defect', 'install', 'others', 'performance', 'security', 'standard'], dest='type', help='type 参数')
    p_edit.add_argument('--affected-build', action='append', dest='affected_build', help='affected-build 参数')
    p_edit_g_steps = p_edit.add_mutually_exclusive_group(required=False)
    p_edit_g_steps.add_argument('--steps', dest='steps', type=str, help='steps 参数')
    p_edit_g_steps.add_argument('--steps-file', dest='steps_file', help="从 UTF-8 文件读取文本")
    p_edit.add_argument('--project', type=positive_int, dest='project', help='project 参数')
    p_edit.add_argument('--execution', type=positive_int, dest='execution', help='execution 参数')
    p_edit.add_argument('--story', type=non_negative_int, dest='story', help='story 参数；允许 0 表示解除关联')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取产品 Bug 列表')
    p_list_scope = p_list.add_mutually_exclusive_group(required=True)
    p_list_scope.add_argument("--product", type=positive_int, dest='product', help='product scope ID')
    p_list_scope.add_argument("--project", type=positive_int, dest='project', help='project scope ID')
    p_list_scope.add_argument("--execution", type=positive_int, dest='execution', help='execution scope ID')
    p_list.add_argument('--branch', type=positive_int, dest='branch', help='branch 参数')
    p_list.add_argument('--browse', type=str, dest='browse', help='browse 参数')
    p_list.add_argument('--module', type=positive_int, dest='module', help='module 参数')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--filters', type=str, dest='filters', help='filters 参数')
    p_list.add_argument('--group-join', type=str, dest='group_join', help='group-join 参数')
    p_list.add_argument('--execution-filter', type=positive_int, dest='execution_filter', help='execution-filter 参数')
    p_list.add_argument('--param', type=positive_int, dest='param', help='param 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)
    p_view = resource_subparsers.add_parser('view', help='获取 Bug 详情')
    p_view.add_argument("id", type=positive_int, help="资源 ID")
    add_json_flag(p_view)
    p_view.set_defaults(_handler=_run_view)
    p_resolve = resource_subparsers.add_parser('resolve', help='解决 Bug')
    p_resolve.add_argument("id", type=positive_int, help="资源 ID")
    p_resolve.add_argument('--resolution', type=str, required=True, choices=['by-design', 'duplicate', 'external', 'fixed', 'not-repro', 'postponed', 'to-story', 'will-not-fix'], dest='resolution', help='resolution 参数')
    p_resolve.add_argument('--resolved-date', type=str, dest='resolved_date', help='resolved-date 参数')
    p_resolve.add_argument('--resolved-build', type=build_ref, dest='resolved_build', help='resolved-build 参数；可为正整数或 trunk')
    p_resolve.add_argument('--duplicate-bug', type=positive_int, dest='duplicate_bug', help='duplicate-bug 参数')
    p_resolve.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_resolve_g_comment = p_resolve.add_mutually_exclusive_group(required=False)
    p_resolve_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_resolve_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_resolve)
    p_resolve.set_defaults(_handler=_run_resolve)
    p_close = resource_subparsers.add_parser('close', help='关闭 Bug')
    p_close.add_argument("id", type=positive_int, help="资源 ID")
    p_close_g_comment = p_close.add_mutually_exclusive_group(required=False)
    p_close_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_close_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_close)
    p_close.set_defaults(_handler=_run_close)
    p_activate = resource_subparsers.add_parser('activate', help='激活 Bug')
    p_activate.add_argument("id", type=positive_int, help="资源 ID")
    p_activate.add_argument('--affected-build', action='append', dest='affected_build', help='affected-build 参数')
    p_activate.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_activate_g_comment = p_activate.add_mutually_exclusive_group(required=False)
    p_activate_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_activate_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_activate)
    p_activate.set_defaults(_handler=_run_activate)
    p_delete = resource_subparsers.add_parser('delete', help='删除 Bug')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: BugsService = getattr(services, 'bug')
    value_type = getattr(args, 'type', None)
    if value_type is not None and value_type not in {'install', 'performance', 'config', 'others', 'security', 'automation', 'standard', 'code-error', 'design-defect'}:
        raise UsageError("--type 不是当前 endpoint 支持的枚举值")
    return service.create(product=getattr(args, 'product', None), title=getattr(args, 'title', None), affected_build=getattr(args, 'affected_build', None), branch=getattr(args, 'branch', None), module=getattr(args, 'module', None), project=getattr(args, 'project', None), execution=getattr(args, 'execution', None), story=getattr(args, 'story', None), task=getattr(args, 'task', None), severity=getattr(args, 'severity', None), priority=getattr(args, 'priority', None), type=getattr(args, 'type', None), os=getattr(args, 'os', None), browser=getattr(args, 'browser', None), steps=resolve_text(args, 'steps'), assignee=getattr(args, 'assignee', None), deadline=getattr(args, 'deadline', None), keywords=getattr(args, 'keywords', None))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: BugsService = getattr(services, 'bug')
    value_type = getattr(args, 'type', None)
    if value_type is not None and value_type not in {'install', 'performance', 'config', 'others', 'security', 'automation', 'standard', 'code-error', 'design-defect'}:
        raise UsageError("--type 不是当前 endpoint 支持的枚举值")
    return service.edit(item_id=args.id, title=getattr(args, 'title', None), severity=getattr(args, 'severity', None), priority=getattr(args, 'priority', None), type=getattr(args, 'type', None), affected_build=getattr(args, 'affected_build', None), steps=resolve_text(args, 'steps'), project=getattr(args, 'project', None), execution=getattr(args, 'execution', None), story=getattr(args, 'story', None))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: BugsService = getattr(services, 'bug')
    if getattr(args, 'product', None) is not None:
        if getattr(args, 'execution_filter', None) is not None or getattr(args, 'param', None) is not None:
            raise UsageError("所选 --product scope 不支持本次提供的某些列表参数")
        return service.list_product(product=getattr(args, 'product'), branch=getattr(args, 'branch', None), browse=getattr(args, 'browse', None), module=getattr(args, 'module', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), page=getattr(args, 'page', None), per_page=getattr(args, 'per_page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    elif getattr(args, 'project', None) is not None:
        if getattr(args, 'branch', None) is not None or getattr(args, 'module', None) is not None:
            raise UsageError("所选 --project scope 不支持本次提供的某些列表参数")
        return service.list_project(project=getattr(args, 'project'), execution_filter=getattr(args, 'execution_filter', None), browse=getattr(args, 'browse', None), param=getattr(args, 'param', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), page=getattr(args, 'page', None), per_page=getattr(args, 'per_page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    elif getattr(args, 'execution', None) is not None:
        if getattr(args, 'branch', None) is not None or getattr(args, 'execution_filter', None) is not None or getattr(args, 'module', None) is not None:
            raise UsageError("所选 --execution scope 不支持本次提供的某些列表参数")
        return service.list_execution(execution=getattr(args, 'execution'), browse=getattr(args, 'browse', None), param=getattr(args, 'param', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), page=getattr(args, 'page', None), per_page=getattr(args, 'per_page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    raise UsageError("必须选择一个列表 scope")

def _run_view(services: object, args: argparse.Namespace) -> object | None:
    service: BugsService = getattr(services, 'bug')
    return service.view(item_id=args.id)

def _run_resolve(services: object, args: argparse.Namespace) -> object | None:
    service: BugsService = getattr(services, 'bug')
    value_resolution = getattr(args, 'resolution', None)
    if value_resolution is not None and value_resolution not in {'not-repro', 'duplicate', 'postponed', 'will-not-fix', 'to-story', 'by-design', 'fixed', 'external'}:
        raise UsageError("--resolution 不是当前 endpoint 支持的枚举值")
    return service.resolve(item_id=args.id, resolution=getattr(args, 'resolution', None), resolved_date=getattr(args, 'resolved_date', None), resolved_build=getattr(args, 'resolved_build', None), duplicate_bug=getattr(args, 'duplicate_bug', None), assignee=getattr(args, 'assignee', None), comment=resolve_text(args, 'comment'))

def _run_close(services: object, args: argparse.Namespace) -> object | None:
    service: BugsService = getattr(services, 'bug')
    return service.close(item_id=args.id, comment=resolve_text(args, 'comment'))

def _run_activate(services: object, args: argparse.Namespace) -> object | None:
    service: BugsService = getattr(services, 'bug')
    return service.activate(item_id=args.id, affected_build=getattr(args, 'affected_build', None), assignee=getattr(args, 'assignee', None), comment=resolve_text(args, 'comment'))

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: BugsService = getattr(services, 'bug')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
