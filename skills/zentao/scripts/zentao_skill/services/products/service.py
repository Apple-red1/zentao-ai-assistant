from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.products import ProductsAPI


class ProductsService:
    ENDPOINT_IDS = ProductsAPI.ENDPOINT_IDS

    def __init__(self, api: ProductsAPI) -> None:
        self.api = api

    def create(self, *, name: object | None, acl: object | None = None, desc: list[object] | None = None, line: object | None = None, po: object | None = None, program: object | None = None, qd: object | None = None, rd: object | None = None, reviewer: list[object] | None = None, type: object | None = None) -> object | None:
        return self.api.create(name=name, program=program, line=line, type=type, po=po, reviewer=reviewer, desc=desc, qd=qd, rd=rd, acl=acl)

    def edit(self, *, item_id: int, name: object | None, acl: object | None = None, desc: list[object] | None = None, line: object | None = None, po: object | None = None, program: object | None = None, qd: object | None = None, rd: object | None = None, reviewer: list[object] | None = None, type: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, name=name, program=program, line=line, type=type, po=po, reviewer=reviewer, desc=desc, qd=qd, rd=rd, acl=acl)

    def list(self, *, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list(browse=browse, sort=sort, order=order, per_page=per_page, page=page)

    def list_program(self, *, program: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_program(program=program, browse=browse, sort=sort, order=order, per_page=per_page, page=page)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
