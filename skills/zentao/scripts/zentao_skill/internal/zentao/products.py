from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class ProductsAPI:
    ENDPOINT_IDS = frozenset({'product.delete', 'product.edit', 'product.list_program', 'product.view', 'product.create', 'product.list'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @staticmethod
    def _description_value(value: object | None) -> object | None:
        """Send ZenTao's scalar product description, even for legacy list input."""
        if not isinstance(value, list):
            return value
        if len(value) == 1:
            return value[0]
        return "\n".join(str(item) for item in value)

    @endpoint('product.create')
    def create(self, *, name: object | None, acl: object | None = None, desc: list[object] | None = None, line: object | None = None, po: object | None = None, program: object | None = None, qd: object | None = None, rd: object | None = None, reviewer: list[object] | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'program': map_enum('program', program),
            'line': map_enum('line', line),
            'type': map_enum('type', type),
            'PO': map_enum('PO', po),
            'reviewer': map_enum('reviewer', reviewer),
            'desc': map_enum('desc', self._description_value(desc)),
            'QD': map_enum('QD', qd),
            'RD': map_enum('RD', rd),
            'acl': map_enum('acl', acl),
        })
        return self.session.post('/products', body=body)

    @endpoint('product.edit')
    def edit(self, *, item_id: int, name: object | None, acl: object | None = None, desc: list[object] | None = None, line: object | None = None, po: object | None = None, program: object | None = None, qd: object | None = None, rd: object | None = None, reviewer: list[object] | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'program': map_enum('program', program),
            'line': map_enum('line', line),
            'type': map_enum('type', type),
            'PO': map_enum('PO', po),
            'reviewer': map_enum('reviewer', reviewer),
            'desc': map_enum('desc', self._description_value(desc)),
            'QD': map_enum('QD', qd),
            'RD': map_enum('RD', rd),
            'acl': map_enum('acl', acl),
        })
        return self.session.put(f'/products/{item_id}', body=body)

    @endpoint('product.list')
    def list(self, *, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
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
        return self.session.get('/products', query=query)

    @endpoint('product.list_program')
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
        return self.session.get(f'/programs/{program}/products', query=query)

    @endpoint('product.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/products/{item_id}')

    @endpoint('product.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/products/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
