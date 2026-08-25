from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.releases import ReleasesAPI


class ReleasesService:
    ENDPOINT_IDS = ReleasesAPI.ENDPOINT_IDS

    def __init__(self, api: ReleasesAPI) -> None:
        self.api = api

    def create(self, *, build: list[object] | None, date: object | None, name: object | None, product: object | None, system: object | None, desc: object | None = None, released_date: object | None = None, status: object | None = None) -> object | None:
        return self.api.create(product=product, system=system, name=name, build=build, status=status, date=date, released_date=released_date, desc=desc)

    def edit(self, *, build: list[object] | None, date: object | None, item_id: int, name: object | None, product: object | None, system: object | None, desc: object | None = None, released_date: object | None = None, status: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, product=product, system=system, name=name, build=build, status=status, date=date, released_date=released_date, desc=desc)

    def list_product(self, *, product: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_product(product=product, browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
