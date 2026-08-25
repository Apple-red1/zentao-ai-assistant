from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class ProgramsAPI:
    ENDPOINT_IDS = frozenset({'program.delete', 'program.list', 'program.edit', 'program.view', 'program.create'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('program.create')
    def create(self, *, begin: object | None, end: object | None, name: object | None, desc: object | None = None, pm: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'PM': map_enum('PM', pm),
            'desc': map_enum('desc', desc),
        })
        return self.session.post('/programs', body=body)

    @endpoint('program.edit')
    def edit(self, *, begin: object | None, end: object | None, item_id: int, name: object | None, desc: object | None = None, pm: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'PM': map_enum('PM', pm),
            'desc': map_enum('desc', desc),
        })
        return self.session.put(f'/programs/{item_id}', body=body)

    @endpoint('program.list')
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
        return self.session.get('/programs', query=query)

    @endpoint('program.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/programs/{item_id}')

    @endpoint('program.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/programs/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
