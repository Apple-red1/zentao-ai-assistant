from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class TestTasksAPI:
    ENDPOINT_IDS = frozenset({'test-task.delete', 'test-task.edit', 'test-task.list_product', 'test-task.list_project', 'test-task.create', 'test-task.list_execution'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('test-task.create')
    def create(self, *, begin: object | None, build: object | None, end: object | None, name: object | None, product: object | None, desc: object | None = None, execution: object | None = None, owner: object | None = None, status: object | None = None, type: list[object] | None = None) -> object | None:
        body = compact_dict({
            'productID': map_enum('productID', product),
            'product': map_enum('product', product),
            'name': map_enum('name', name),
            'build': map_enum('build', build),
            'execution': map_enum('execution', execution),
            'type': map_enum('type', type),
            'owner': map_enum('owner', owner),
            'status': map_enum('status', status),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'desc': map_enum('desc', desc),
        })
        return self.session.post('/testtasks', body=body)

    @endpoint('test-task.edit')
    def edit(self, *, begin: object | None, build: object | None, end: object | None, item_id: int, name: object | None, desc: object | None = None, execution: object | None = None, owner: object | None = None, status: object | None = None, type: list[object] | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'build': map_enum('build', build),
            'execution': map_enum('execution', execution),
            'type': map_enum('type', type),
            'owner': map_enum('owner', owner),
            'status': map_enum('status', status),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'desc': map_enum('desc', desc),
        })
        return self.session.put(f'/testtasks/{item_id}', body=body)

    @endpoint('test-task.list_product')
    def list_product(self, *, product: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
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
        return self.session.get(f'/products/{product}/testtasks', query=query)

    @endpoint('test-task.list_project')
    def list_project(self, *, project: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
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
        return self.session.get(f'/projects/{project}/testtasks', query=query)

    @endpoint('test-task.list_execution')
    def list_execution(self, *, execution: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
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
        return self.session.get(f'/executions/{execution}/testtasks', query=query)

    @endpoint('test-task.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/testtasks/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
