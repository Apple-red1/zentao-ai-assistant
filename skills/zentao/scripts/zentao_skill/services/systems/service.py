from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.systems import SystemsAPI


class SystemsService:
    ENDPOINT_IDS = SystemsAPI.ENDPOINT_IDS

    def __init__(self, api: SystemsAPI) -> None:
        self.api = api

    def create(self, *, child: list[object] | None, integrated: object | None, name: object | None, product: object | None, desc: object | None = None) -> object | None:
        return self.api.create(product=product, integrated=integrated, child=child, name=name, desc=desc)

    def edit(self, *, child: list[object] | None, item_id: int, name: object | None, desc: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, name=name, child=child, desc=desc)

    def list_product(self, *, product: int, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_product(product=product, sort=sort, order=order, per_page=per_page, page=page)
