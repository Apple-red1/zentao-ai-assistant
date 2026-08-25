from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.programs import ProgramsAPI


class ProgramsService:
    ENDPOINT_IDS = ProgramsAPI.ENDPOINT_IDS

    def __init__(self, api: ProgramsAPI) -> None:
        self.api = api

    def create(self, *, begin: object | None, end: object | None, name: object | None, desc: object | None = None, pm: object | None = None) -> object | None:
        return self.api.create(name=name, begin=begin, end=end, pm=pm, desc=desc)

    def edit(self, *, begin: object | None, end: object | None, item_id: int, name: object | None, desc: object | None = None, pm: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, name=name, begin=begin, end=end, pm=pm, desc=desc)

    def list(self, *, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list(browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
