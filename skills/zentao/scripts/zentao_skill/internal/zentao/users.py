from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class UsersAPI:
    ENDPOINT_IDS = frozenset({'user.list', 'user.view', 'user.edit', 'user.delete', 'user.create'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('user.create')
    def create(self, *, account: object | None, password: object | None, realname: object | None, vision: list[object] | None = None) -> object | None:
        body = compact_dict({
            'account': map_enum('account', account),
            'realname': map_enum('realname', realname),
            'password': map_enum('password', password),
            'visions': map_enum('visions', vision or ['rnd']),
        })
        return self.session.post('/users', body=body)

    @endpoint('user.edit')
    def edit(self, *, account: object | None, item_id: int, dept: object | None = None, email: object | None = None, group: list[object] | None = None, join: object | None = None, mobile: object | None = None, password: object | None = None, realname: object | None = None, vision: list[object] | None = None, weixin: object | None = None) -> object | None:
        body = compact_dict({
            'account': map_enum('account', account),
            'realname': map_enum('realname', realname),
            'dept': map_enum('dept', dept),
            'join': map_enum('join', join),
            'group': map_enum('group', group),
            'email': map_enum('email', email),
            'visions': map_enum('visions', vision),
            'mobile': map_enum('mobile', mobile),
            'weixin': map_enum('weixin', weixin),
            'password': map_enum('password', password),
        })
        return self.session.put(f'/users/{item_id}', body=body)

    @endpoint('user.list')
    def list(self, *, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'browseType': map_enum('browseType', browse),
            'recPerPage': map_enum('recPerPage', per_page),
            'pageID': map_enum('pageID', page),
            'filters': map_enum('filters', filters),
            'groupJoin': map_enum('groupJoin', group_join),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get('/users', query=query)

    @endpoint('user.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/users/{item_id}')

    @endpoint('user.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/users/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
