from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.tasks.service import TasksService
from ..common import add_json_flag, auto_value, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'task.start', 'task.create', 'task.close', 'task.activate', 'task.delete', 'task.finish', 'task.list_execution', 'task.view', 'task.edit'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建任务')
    p_create.add_argument('--name', type=str, required=True, dest='name', help='name 参数')
    p_create.add_argument('--execution', type=positive_int, required=True, dest='execution', help='execution 参数')
    p_create.add_argument('--type', type=str, dest='type', help='type 参数')
    p_create.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_create.add_argument('--estimated-start', type=str, dest='estimated_start', help='estimated-start 参数')
    p_create.add_argument('--deadline', type=str, dest='deadline', help='deadline 参数')
    p_create.add_argument('--priority', type=positive_int, dest='priority', help='priority 参数')
    p_create.add_argument('--estimate', type=number, dest='estimate', help='estimate 参数')
    p_create.add_argument('--module', type=positive_int, dest='module', help='module 参数')
    p_create.add_argument('--story', type=positive_int, dest='story', help='story 参数')
    p_create_g_desc = p_create.add_mutually_exclusive_group(required=False)
    p_create_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_create_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    p_create.add_argument('--parent', type=positive_int, dest='parent', help='parent 参数')
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改任务')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--name', type=str, dest='name', help='name 参数')
    p_edit.add_argument('--type', type=str, dest='type', help='type 参数')
    p_edit.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_edit.add_argument('--estimated-start', type=str, dest='estimated_start', help='estimated-start 参数')
    p_edit.add_argument('--deadline', type=str, dest='deadline', help='deadline 参数')
    p_edit.add_argument('--priority', type=positive_int, dest='priority', help='priority 参数')
    p_edit.add_argument('--estimate', type=number, dest='estimate', help='estimate 参数')
    p_edit.add_argument('--module', type=positive_int, dest='module', help='module 参数')
    p_edit.add_argument('--story', type=positive_int, dest='story', help='story 参数')
    p_edit_g_desc = p_edit.add_mutually_exclusive_group(required=False)
    p_edit_g_desc.add_argument('--desc', dest='desc', type=str, help='desc 参数')
    p_edit_g_desc.add_argument('--desc-file', dest='desc_file', help="从 UTF-8 文件读取文本")
    p_edit.add_argument('--parent', type=positive_int, dest='parent', help='parent 参数')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取执行任务列表')
    p_list_scope = p_list.add_mutually_exclusive_group(required=True)
    p_list_scope.add_argument("--execution", type=positive_int, dest='execution', help='execution scope ID')
    p_list.add_argument('--browse', type=str, dest='browse', help='browse 参数')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)
    p_view = resource_subparsers.add_parser('view', help='获取任务详情')
    p_view.add_argument("id", type=positive_int, help="资源 ID")
    add_json_flag(p_view)
    p_view.set_defaults(_handler=_run_view)
    p_start = resource_subparsers.add_parser('start', help='启动任务')
    p_start.add_argument("id", type=positive_int, help="资源 ID")
    p_start.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_start.add_argument('--real-started', type=str, required=True, dest='real_started', help='real-started 参数')
    p_start.add_argument('--consumed', type=number, dest='consumed', help='consumed 参数')
    p_start.add_argument('--left', type=number, dest='left', help='left 参数')
    p_start_g_comment = p_start.add_mutually_exclusive_group(required=False)
    p_start_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_start_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_start)
    p_start.set_defaults(_handler=_run_start)
    p_finish = resource_subparsers.add_parser('finish', help='完成任务')
    p_finish.add_argument("id", type=positive_int, help="资源 ID")
    p_finish.add_argument('--current-consumed', type=number, required=True, dest='current_consumed', help='current-consumed 参数')
    p_finish.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_finish.add_argument('--consumed', type=number, dest='consumed', help='consumed 参数')
    p_finish.add_argument('--real-started', type=str, required=True, dest='real_started', help='real-started 参数')
    p_finish.add_argument('--finished-date', type=str, required=True, dest='finished_date', help='finished-date 参数')
    p_finish_g_comment = p_finish.add_mutually_exclusive_group(required=False)
    p_finish_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_finish_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_finish)
    p_finish.set_defaults(_handler=_run_finish)
    p_close = resource_subparsers.add_parser('close', help='关闭任务')
    p_close.add_argument("id", type=positive_int, help="资源 ID")
    p_close_g_comment = p_close.add_mutually_exclusive_group(required=False)
    p_close_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_close_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_close)
    p_close.set_defaults(_handler=_run_close)
    p_activate = resource_subparsers.add_parser('activate', help='激活任务')
    p_activate.add_argument("id", type=positive_int, help="资源 ID")
    p_activate.add_argument('--left', type=number, dest='left', help='left 参数')
    p_activate.add_argument('--assignee', type=str, dest='assignee', help='assignee 参数')
    p_activate_g_comment = p_activate.add_mutually_exclusive_group(required=False)
    p_activate_g_comment.add_argument('--comment', dest='comment', type=str, help='comment 参数')
    p_activate_g_comment.add_argument('--comment-file', dest='comment_file', help="从 UTF-8 文件读取文本")
    add_json_flag(p_activate)
    p_activate.set_defaults(_handler=_run_activate)
    p_delete = resource_subparsers.add_parser('delete', help='删除任务')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: TasksService = getattr(services, 'task')
    return service.create(name=getattr(args, 'name', None), execution=getattr(args, 'execution', None), type=getattr(args, 'type', None), assignee=getattr(args, 'assignee', None), estimated_start=getattr(args, 'estimated_start', None), deadline=getattr(args, 'deadline', None), priority=getattr(args, 'priority', None), estimate=getattr(args, 'estimate', None), module=getattr(args, 'module', None), story=getattr(args, 'story', None), desc=resolve_text(args, 'desc'), parent=getattr(args, 'parent', None))

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: TasksService = getattr(services, 'task')
    return service.edit(item_id=args.id, name=getattr(args, 'name', None), type=getattr(args, 'type', None), assignee=getattr(args, 'assignee', None), estimated_start=getattr(args, 'estimated_start', None), deadline=getattr(args, 'deadline', None), priority=getattr(args, 'priority', None), estimate=getattr(args, 'estimate', None), module=getattr(args, 'module', None), story=getattr(args, 'story', None), desc=resolve_text(args, 'desc'), parent=getattr(args, 'parent', None))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: TasksService = getattr(services, 'task')
    if getattr(args, 'execution', None) is not None:
        return service.list_execution(execution=getattr(args, 'execution'), browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None))
    raise UsageError("必须选择一个列表 scope")

def _run_view(services: object, args: argparse.Namespace) -> object | None:
    service: TasksService = getattr(services, 'task')
    return service.view(item_id=args.id)

def _run_start(services: object, args: argparse.Namespace) -> object | None:
    service: TasksService = getattr(services, 'task')
    return service.start(item_id=args.id, assignee=getattr(args, 'assignee', None), real_started=getattr(args, 'real_started', None), consumed=getattr(args, 'consumed', None), left=getattr(args, 'left', None), comment=resolve_text(args, 'comment'))

def _run_finish(services: object, args: argparse.Namespace) -> object | None:
    service: TasksService = getattr(services, 'task')
    return service.finish(item_id=args.id, current_consumed=getattr(args, 'current_consumed', None), assignee=getattr(args, 'assignee', None), consumed=getattr(args, 'consumed', None), real_started=getattr(args, 'real_started', None), finished_date=getattr(args, 'finished_date', None), comment=resolve_text(args, 'comment'))

def _run_close(services: object, args: argparse.Namespace) -> object | None:
    service: TasksService = getattr(services, 'task')
    return service.close(item_id=args.id, comment=resolve_text(args, 'comment'))

def _run_activate(services: object, args: argparse.Namespace) -> object | None:
    service: TasksService = getattr(services, 'task')
    return service.activate(item_id=args.id, left=getattr(args, 'left', None), assignee=getattr(args, 'assignee', None), comment=resolve_text(args, 'comment'))

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: TasksService = getattr(services, 'task')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
