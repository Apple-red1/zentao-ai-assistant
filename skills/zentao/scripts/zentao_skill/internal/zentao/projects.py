from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class ProjectsAPI:
    ENDPOINT_IDS = frozenset({'project.create', 'project.delete', 'project.list', 'project.list_program', 'project.edit'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('project.create')
    def create(self, *, begin: object | None, end: object | None, model: object | None, name: object | None, parent: object | None = None, pm: object | None = None, product: list[object] | None = None, workflow_group: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'model': map_enum('model', model),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'products': map_enum('products', product),
            'parent': map_enum('parent', parent),
            'workflowGroup': map_enum('workflowGroup', workflow_group),
            'PM': map_enum('PM', pm),
        })
        return self.session.post('/projects', body=body)

    @endpoint('project.edit')
    def edit(self, *, begin: object | None, end: object | None, item_id: int, model: object | None, name: object | None, parent: object | None = None, pm: object | None = None, product: list[object] | None = None, workflow_group: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'model': map_enum('model', model),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'products': map_enum('products', product),
            'parent': map_enum('parent', parent),
            'workflowGroup': map_enum('workflowGroup', workflow_group),
            'PM': map_enum('PM', pm),
        })
        return self.session.put(f'/projects/{item_id}', body=body)

    @endpoint('project.list')
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
        return self.session.get('/projects', query=query)

    @endpoint('project.list_program')
    def list_program(self, *, program: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'browseType': map_enum('browseType', browse),
            'recPerPage': map_enum('recPerPage', per_page),
            'pageID': map_enum('pageID', page),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/programs/{program}/projects', query=query)

    @endpoint('project.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/projects/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
