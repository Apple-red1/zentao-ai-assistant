from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.product_plans import ProductPlansAPI


class ProductPlansService:
    ENDPOINT_IDS = ProductPlansAPI.ENDPOINT_IDS

    def __init__(self, api: ProductPlansAPI) -> None:
        self.api = api

    def create(self, *, product: object | None, title: object | None, begin: object | None = None, branch: object | None = None, desc: object | None = None, end: object | None = None, parent: object | None = None) -> object | None:
        return self.api.create(product=product, title=title, parent=parent, begin=begin, end=end, branch=branch, desc=desc)

    def edit(self, *, item_id: int, title: object | None, begin: object | None = None, branch: object | None = None, desc: object | None = None, end: object | None = None, parent: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, title=title, parent=parent, begin=begin, end=end, branch=branch, desc=desc)

    def list_product(self, *, product: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_product(product=product, browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
