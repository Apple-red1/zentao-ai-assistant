from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class TestCasesAPI:
    ENDPOINT_IDS = frozenset({'test-case.list_project', 'test-case.view', 'test-case.delete', 'test-case.list_execution', 'test-case.list_product', 'test-case.create', 'test-case.edit'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('test-case.create')
    def create(self, *, product: object | None, title: object | None, execution: object | None = None, expect: list[object] | None = None, module: object | None = None, precondition: object | None = None, priority: object | None = None, project: object | None = None, step: list[object] | None = None, step_type: list[object] | None = None, story: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'productID': map_enum('productID', product),
            'product': map_enum('product', product),
            'title': map_enum('title', title),
            'module': map_enum('module', module),
            'story': map_enum('story', story),
            'pri': map_enum('pri', priority),
            'type': map_enum('type', type),
            'precondition': map_enum('precondition', precondition),
            'steps': map_enum('steps', step),
            'expects': map_enum('expects', expect),
            'stepType': map_enum('stepType', step_type),
            'project': map_enum('project', project),
            'execution': map_enum('execution', execution),
        })
        return self.session.post('/testcases', body=body)

    @endpoint('test-case.edit')
    def edit(self, *, item_id: int, title: object | None, expect: list[object] | None = None, module: object | None = None, precondition: object | None = None, priority: object | None = None, step: list[object] | None = None, step_type: list[object] | None = None, story: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'title': map_enum('title', title),
            'module': map_enum('module', module),
            'story': map_enum('story', story),
            'pri': map_enum('pri', priority),
            'type': map_enum('type', type),
            'precondition': map_enum('precondition', precondition),
            'steps': map_enum('steps', step),
            'expects': map_enum('expects', expect),
            'stepType': map_enum('stepType', step_type),
        })
        return self.session.put(f'/testcases/{item_id}', body=body)

    @endpoint('test-case.list_product')
    def list_product(self, *, product: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
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
        return self.session.get(f'/products/{product}/testcases', query=query)

    @endpoint('test-case.list_project')
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
        return self.session.get(f'/projects/{project}/testcases', query=query)

    @endpoint('test-case.list_execution')
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
        return self.session.get(f'/executions/{execution}/testcases', query=query)

    @endpoint('test-case.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/testcases/{item_id}')

    @endpoint('test-case.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/testcases/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
