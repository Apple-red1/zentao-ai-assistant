from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class SystemsAPI:
    ENDPOINT_IDS = frozenset({'system.list_product', 'system.edit', 'system.create'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('system.create')
    def create(self, *, child: list[object] | None, integrated: object | None, name: object | None, product: object | None, desc: object | None = None) -> object | None:
        body = compact_dict({
            'productID': map_enum('productID', product),
            'integrated': map_enum('integrated', integrated),
            'children': map_enum('children', child),
            'name': map_enum('name', name),
            'desc': map_enum('desc', desc),
        })
        return self.session.post('/systems', body=body)

    @endpoint('system.edit')
    def edit(self, *, child: list[object] | None, item_id: int, name: object | None, desc: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'children': map_enum('children', child),
            'desc': map_enum('desc', desc),
        })
        return self.session.put(f'/systems/{item_id}', body=body)

    @endpoint('system.list_product')
    def list_product(self, *, product: int, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'recPerPage': map_enum('recPerPage', per_page),
            'pageID': map_enum('pageID', page),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/products/{product}/systems', query=query)
