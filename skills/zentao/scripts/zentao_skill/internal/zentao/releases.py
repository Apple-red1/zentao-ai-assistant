from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class ReleasesAPI:
    ENDPOINT_IDS = frozenset({'release.create', 'release.list_product', 'release.delete', 'release.edit'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('release.create')
    def create(self, *, build: list[object] | None, date: object | None, name: object | None, product: object | None, system: object | None, desc: object | None = None, status: object | None = None) -> object | None:
        body = compact_dict({
            'productID': map_enum('productID', product),
            'system': map_enum('system', system),
            'name': map_enum('name', name),
            'build': map_enum('build', build),
            'status': map_enum('status', status),
            'date': map_enum('date', date),
            'desc': map_enum('desc', desc),
        })
        return self.session.post('/releases', body=body)

    @endpoint('release.edit')
    def edit(self, *, build: list[object] | None, date: object | None, item_id: int, name: object | None, system: object | None, desc: object | None = None, status: object | None = None) -> object | None:
        body = compact_dict({
            'system': map_enum('system', system),
            'name': map_enum('name', name),
            'build': map_enum('build', build),
            'status': map_enum('status', status),
            'date': map_enum('date', date),
            'desc': map_enum('desc', desc),
        })
        return self.session.put(f'/releases/{item_id}', body=body)

    @endpoint('release.list_product')
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
        return self.session.get(f'/products/{product}/releases', query=query)

    @endpoint('release.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/releases/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
