from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.stories.service import StoriesService
from ..common import add_json_flag, auto_value, non_negative_int, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'story.list_product', 'story.list_execution', 'story.delete', 'story.list_project', 'story.create', 'story.view', 'story.activate', 'story.change', 'story.edit', 'story.close'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建研发需求')
    p_create.add_argument('--product', type=positive_int, required=True, dest='product', help='product 参数')
    p_create.add_argument('--title', type=str, required=True, dest='title', help='title 参数')
    p_create.add_argument('--priority', type=positive_int, dest='priority', help='priority 参数')
    p_create.add_argument('--module', type=non_negative_int, dest='module', help='module 参数；允许 0 表示根模块')
    p_create.add_argument('--parent', type=non_negative_int, dest='parent', help='parent 参数；允许 0 表示无父需求')
    p_create.add_argument('--estimate', type=number, dest='estimate', help='estimate 参数')
    p_create_g_spec = p_create.add_mutually_exclusive_group(required=False)
    p_create_g_spec.add_argument('--spec', dest='spec', type=str, help='spec 参数')
    p_create_g_spec.add_argument('--spec-file', dest='spec_file', help="从 UTF-8 文件读取文本")
    p_create.add_argument('--category', type=str, choices=['experience', 'feature', 'improve', 'interface', 'other', 'performance', 'safe'], dest='category', help='category 参数')
    p_create.add_argument('--source', type=str, choices=['bug', 'competitor', 'customer', 'dev', 'forum', 'market', 'operation', 'other', 'partner', 'po', 'service', 'support', 'tester', 'user'], dest='source', help='source 参数')
    p_create_g_verify = p_create.add_mutually_exclusive_group(required=False)
    p_create_g_verify.add_argument('--verify', dest='verify', type=str, help='verify 参数')
    p_create_g_verify.add_argument('--verify-file', dest='verify_file', help="从 UTF-8 文件读取文本")
    p_create.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_create.add_argument('--reviewer', action='append', dest='reviewer', help='reviewer 参数')
    p_create.add_argument('--project', type=positive_int, dest='project', help='project 参数')
    p_create.add_argument('--execution', type=non_negative_int, dest='execution', help='execution 参数；允许 0 表示无执行')
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改研发需求')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--title', type=str, required=True, dest='title', help='title 参数')
    p_edit.add_argument('--priority', type=positive_int, dest='priority', help='priority 参数')
    p_edit.add_argument('--module', type=non_negative_int, dest='module', help='module 参数；允许 0 表示根模块')
    p_edit.add_argument('--parent', type=non_negative_int, dest='parent', help='parent 参数；允许 0 表示无父需求')
    p_edit.add_argument('--estimate', type=number, dest='estimate', help='estimate 参数')
    p_edit.add_argument('--category', type=str, dest='category', help='category 参数')
    p_edit.add_argument('--source', type=str, dest='source', help='source 参数')
    p_edit.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_edit.add_argument('--plan', type=positive_int, dest='plan', help='plan 参数')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_change = resource_subparsers.add_parser('change', help='变更研发需求')
    p_change.add_argument("id", type=positive_int, help="资源 ID")
    p_change.add_argument('--title', type=str, dest='title', help='title 参数')
    p_change.add_argument('--reviewer', action='append', required=True, dest='reviewer', help='reviewer 参数')
    p_change_g_spec = p_change.add_mutually_exclusive_group(required=False)
    p_change_g_spec.add_argument('--spec', dest='spec', type=str, help='spec 参数')
    p_change_g_spec.add_argument('--spec-file', dest='spec_file', help="从 UTF-8 文件读取文本")
    p_change_g_verify = p_change.add_mutually_exclusive_group(required=False)
    p_change_g_verify.add_argument('--verify', dest='verify', type=str, help='verify 参数')
    p_change_g_verify.add_argument('--verify-file', dest='verify_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_change)
    p_change.set_defaults(_handler=_run_change)
    p_list = resource_subparsers.add_parser('list', help='获取产品研发需求列表')
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
    p_view = resource_subparsers.add_parser('view', help='获取研发需求详情')
    p_view.add_argument("id", type=positive_int, help="资源 ID")
    add_json_flag(p_view)
    p_view.set_defaults(_handler=_run_view)
    p_close = resource_subparsers.add_parser('close', help='关闭研发需求')
    p_close.add_argument("id", type=positive_int, help="资源 ID")
    p_close.add_argument('--closed-reason', type=str, required=True, choices=['by-design', 'cancel', 'done', 'duplicate', 'postponed', 'subdivided', 'will-not-do'], dest='closed_reason', help='closed-reason 参数')
    p_close_g_comment = p_close.add_mutually_exclusive_group(required=False)
    p_close_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_close_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_close)
    p_close.set_defaults(_handler=_run_close)
    p_activate = resource_subparsers.add_parser('activate', help='激活研发需求')
    p_activate.add_argument("id", type=positive_int, help="资源 ID")
    p_activate.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_activate_g_comment = p_activate.add_mutually_exclusive_group(required=False)
    p_activate_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_activate_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_activate)
    p_activate.set_defaults(_handler=_run_activate)
    p_delete = resource_subparsers.add_parser('delete', help='删除研发需求')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: StoriesService = getattr(services, 'story')
    value_category = getattr(args, 'category', None)
    if value_category is not None and value_category not in {'interface', 'experience', 'improve', 'performance', 'other', 'feature', 'safe'}:
        raise UsageError("--category 不是当前 endpoint 支持的枚举值")
    value_source = getattr(args, 'source', None)
    if value_source is not None and value_source not in {'po', 'market', 'dev', 'competitor', 'service', 'customer', 'other', 'user', 'support', 'partner', 'forum', 'bug', 'operation', 'tester'}:
        raise UsageError("--source 不是当前 endpoint 支持的枚举值")
    return service.create(product=getattr(args, 'product', None), title=getattr(args, 'title', None), priority=getattr(args, 'priority', None), module=getattr(args, 'module', None), parent=getattr(args, 'parent', None), estimate=getattr(args, 'estimate', None), spec=resolve_text(args, 'spec'), category=getattr(args, 'category', None), source=getattr(args, 'source', None), verify=resolve_text(args, 'verify'), assignee=getattr(args, 'assignee', None), reviewer=getattr(args, 'reviewer', None), project=getattr(args, 'project', None), execution=getattr(args, 'execution', None))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: StoriesService = getattr(services, 'story')
    return service.edit(item_id=args.id, title=getattr(args, 'title', None), priority=getattr(args, 'priority', None), module=getattr(args, 'module', None), parent=getattr(args, 'parent', None), estimate=getattr(args, 'estimate', None), category=getattr(args, 'category', None), source=getattr(args, 'source', None), assignee=getattr(args, 'assignee', None), plan=getattr(args, 'plan', None))

def _run_change(services: object, args: argparse.Namespace) -> object | None:
    service: StoriesService = getattr(services, 'story')
    return service.change(item_id=args.id, title=getattr(args, 'title', None), reviewer=getattr(args, 'reviewer', None), spec=resolve_text(args, 'spec'), verify=resolve_text(args, 'verify'))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: StoriesService = getattr(services, 'story')
    if getattr(args, 'product', None) is not None:
        return service.list_product(product=getattr(args, 'product'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    elif getattr(args, 'project', None) is not None:
        return service.list_project(project=getattr(args, 'project'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    elif getattr(args, 'execution', None) is not None:
        return service.list_execution(execution=getattr(args, 'execution'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))
    raise UsageError("必须选择一个列表 scope")

def _run_view(services: object, args: argparse.Namespace) -> object | None:
    service: StoriesService = getattr(services, 'story')
    return service.view(item_id=args.id)

def _run_close(services: object, args: argparse.Namespace) -> object | None:
    service: StoriesService = getattr(services, 'story')
    value_closed_reason = getattr(args, 'closed_reason', None)
    if value_closed_reason is not None and value_closed_reason not in {'duplicate', 'done', 'cancel', 'postponed', 'will-not-do', 'subdivided', 'by-design'}:
        raise UsageError("--closed-reason 不是当前 endpoint 支持的枚举值")
    return service.close(item_id=args.id, closed_reason=getattr(args, 'closed_reason', None), comment=resolve_text(args, 'comment'))

def _run_activate(services: object, args: argparse.Namespace) -> object | None:
    service: StoriesService = getattr(services, 'story')
    return service.activate(item_id=args.id, assignee=getattr(args, 'assignee', None), comment=resolve_text(args, 'comment'))

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: StoriesService = getattr(services, 'story')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
