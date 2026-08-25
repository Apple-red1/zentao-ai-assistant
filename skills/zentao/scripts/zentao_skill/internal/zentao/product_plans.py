from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class ProductPlansAPI:
    ENDPOINT_IDS = frozenset({'product-plan.delete', 'product-plan.edit', 'product-plan.list_product', 'product-plan.create', 'product-plan.view'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('product-plan.create')
    def create(self, *, product: object | None, title: object | None, begin: object | None = None, branch: object | None = None, desc: object | None = None, end: object | None = None, parent: object | None = None) -> object | None:
        body = compact_dict({
            'productID': map_enum('productID', product),
            'title': map_enum('title', title),
            'parent': map_enum('parent', parent),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'branchID': map_enum('branchID', branch),
            'desc': map_enum('desc', desc),
        })
        return self.session.post('/productplans', body=body)

    @endpoint('product-plan.edit')
    def edit(self, *, item_id: int, title: object | None, begin: object | None = None, branch: object | None = None, desc: object | None = None, end: object | None = None, parent: object | None = None) -> object | None:
        body = compact_dict({
            'title': map_enum('title', title),
            'parent': map_enum('parent', parent),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'branchID': map_enum('branchID', branch),
            'desc': map_enum('desc', desc),
        })
        return self.session.put(f'/productplans/{item_id}', body=body)

    @endpoint('product-plan.list_product')
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
        return self.session.get(f'/products/{product}/productplans', query=query)

    @endpoint('product-plan.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/productplans/{item_id}')

    @endpoint('product-plan.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/productplans/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
