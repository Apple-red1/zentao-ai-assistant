from __future__ import annotations

import argparse

from ...internal.errors import UsageError
from ...services.users.service import UsersService
from ..common import add_json_flag, auto_value, non_negative_int, number, page_int, per_page_int, positive_int, resolve_text


ENDPOINT_IDS = frozenset({'user.list', 'user.view', 'user.edit', 'user.delete', 'user.create'})

def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_create = resource_subparsers.add_parser('create', help='创建用户')
    p_create.add_argument('--account', type=str, required=True, dest='account', help='account 参数')
    p_create.add_argument('--realname', type=str, required=True, dest='realname', help='realname 参数')
    p_create.add_argument('--password', type=str, required=True, dest='password', help='password 参数')
    p_create.add_argument('--vision', action='append', choices=['lite', 'rnd'], dest='vision', help='vision 参数；默认 rnd')
    add_json_flag(p_create)
    p_create.set_defaults(_handler=_run_create)
    p_edit = resource_subparsers.add_parser('edit', help='修改用户信息')
    p_edit.add_argument("id", type=positive_int, help="资源 ID")
    p_edit.add_argument('--account', type=str, required=True, dest='account', help='account 参数')
    p_edit.add_argument('--realname', type=str, dest='realname', help='realname 参数')
    p_edit.add_argument('--dept', type=non_negative_int, dest='dept', help='dept 参数；允许 0 表示无部门')
    p_edit.add_argument('--join', type=str, dest='join', help='join 参数')
    p_edit.add_argument('--group', action='append', dest='group', help='group 参数')
    p_edit.add_argument('--email', type=str, dest='email', help='email 参数')
    p_edit.add_argument('--vision', action='append', choices=['lite', 'rnd'], dest='vision', help='vision 参数')
    p_edit.add_argument('--mobile', type=str, dest='mobile', help='mobile 参数')
    p_edit.add_argument('--weixin', type=str, dest='weixin', help='weixin 参数')
    p_edit.add_argument('--password', type=str, dest='password', help='password 参数')
    add_json_flag(p_edit)
    p_edit.set_defaults(_handler=_run_edit)
    p_list = resource_subparsers.add_parser('list', help='获取用户列表')
    p_list.add_argument('--browse', type=str, dest='browse', help='browse 参数')
    p_list.add_argument("--sort", dest="sort", help="排序字段；与 --order 组合为 API orderBy")
    p_list.add_argument("--order", choices=["asc", "desc"], dest="order", help="排序方向；必须与 --sort 一起使用")
    p_list.add_argument('--per-page', type=per_page_int, dest='per_page', help='per-page 参数')
    p_list.add_argument('--page', type=page_int, dest='page', help='page 参数')
    p_list.add_argument('--filters', type=str, dest='filters', help='filters 参数')
    p_list.add_argument('--group-join', type=str, dest='group_join', help='group-join 参数')
    add_json_flag(p_list)
    p_list.set_defaults(_handler=_run_list)
    p_view = resource_subparsers.add_parser('view', help='获取用户详情')
    p_view.add_argument("id", type=positive_int, help="资源 ID")
    add_json_flag(p_view)
    p_view.set_defaults(_handler=_run_view)
    p_delete = resource_subparsers.add_parser('delete', help='删除用户')
    p_delete.add_argument("id", type=positive_int, help="资源 ID")
    p_delete.add_argument("--yes", action="store_true", help="确认执行不可逆删除")
    add_json_flag(p_delete)
    p_delete.set_defaults(_handler=_run_delete)

def _run_create(services: object, args: argparse.Namespace) -> object | None:
    service: UsersService = getattr(services, 'user')
    value_vision = getattr(args, 'vision', None) or ['rnd']
    if any(v not in {'rnd', 'lite'} for v in value_vision):
        raise UsageError("--vision 包含当前 endpoint 不支持的枚举值")
    return service.create(account=getattr(args, 'account', None), realname=getattr(args, 'realname', None), password=getattr(args, 'password', None), vision=value_vision)

def _run_edit(services: object, args: argparse.Namespace) -> object | None:
    service: UsersService = getattr(services, 'user')
    value_vision = getattr(args, 'vision', None)
    if value_vision is not None and any(v not in {'rnd', 'lite'} for v in value_vision):
        raise UsageError("--vision 包含当前 endpoint 不支持的枚举值")
    return service.edit(item_id=args.id, account=getattr(args, 'account', None), realname=getattr(args, 'realname', None), dept=getattr(args, 'dept', None), join=getattr(args, 'join', None), group=getattr(args, 'group', None), email=getattr(args, 'email', None), vision=getattr(args, 'vision', None), mobile=getattr(args, 'mobile', None), weixin=getattr(args, 'weixin', None), password=getattr(args, 'password', None))

def _run_list(services: object, args: argparse.Namespace) -> object | None:
    service: UsersService = getattr(services, 'user')
    return service.list(browse=getattr(args, 'browse', None), sort=getattr(args, "sort", None), order=getattr(args, "order", None), per_page=getattr(args, 'per_page', None), page=getattr(args, 'page', None), filters=getattr(args, 'filters', None), group_join=getattr(args, 'group_join', None))

def _run_view(services: object, args: argparse.Namespace) -> object | None:
    service: UsersService = getattr(services, 'user')
    return service.view(item_id=args.id)

def _run_delete(services: object, args: argparse.Namespace) -> object | None:
    service: UsersService = getattr(services, 'user')
    if not args.yes:
        raise UsageError("删除操作需要显式 --yes；未确认时不会发送任何 HTTP 请求")
    return service.delete(item_id=args.id)
