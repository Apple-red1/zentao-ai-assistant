from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class BuildsAPI:
    ENDPOINT_IDS = frozenset({'build.list_execution', 'build.list_project', 'build.delete', 'build.edit', 'build.create'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('build.create')
    def create(self, *, builder: object | None, date: object | None, execution: object | None, name: object | None, product: object | None, system: object | None, desc: object | None = None, file_path: object | None = None, scm_path: object | None = None) -> object | None:
        body = compact_dict({
            'executionID': map_enum('executionID', execution),
            'product': map_enum('product', product),
            'name': map_enum('name', name),
            'system': map_enum('system', system),
            'builder': map_enum('builder', builder),
            'date': map_enum('date', date),
            'scmPath': map_enum('scmPath', scm_path),
            'filePath': map_enum('filePath', file_path),
            'desc': map_enum('desc', desc),
        })
        return self.session.post('/builds', body=body)

    @endpoint('build.edit')
    def edit(self, *, builder: object | None, date: object | None, execution: object | None, item_id: int, name: object | None, product: object | None, system: object | None, desc: object | None = None, file_path: object | None = None, scm_path: object | None = None) -> object | None:
        body = compact_dict({
            'execution': map_enum('execution', execution),
            'product': map_enum('product', product),
            'name': map_enum('name', name),
            'system': map_enum('system', system),
            'builder': map_enum('builder', builder),
            'date': map_enum('date', date),
            'scmPath': map_enum('scmPath', scm_path),
            'filePath': map_enum('filePath', file_path),
            'desc': map_enum('desc', desc),
        })
        return self.session.put(f'/builds/{item_id}', body=body)

    @endpoint('build.list_project')
    def list_project(self, *, project: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
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
        return self.session.get(f'/projects/{project}/builds', query=query)

    @endpoint('build.list_execution')
    def list_execution(self, *, execution: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
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
        return self.session.get(f'/executions/{execution}/builds', query=query)

    @endpoint('build.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/builds/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
