from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.tickets import TicketsAPI


class TicketsService:
    ENDPOINT_IDS = TicketsAPI.ENDPOINT_IDS

    def __init__(self, api: TicketsAPI) -> None:
        self.api = api

    def create(self, *, product: object | None, title: object | None, affected_build: list[object] | None = None, assignee: object | None = None, deadline: object | None = None, desc: object | None = None, module: object | None = None, type: object | None = None) -> object | None:
        return self.api.create(product=product, module=module, title=title, type=type, desc=desc, assignee=assignee, deadline=deadline, affected_build=affected_build)

    def edit(self, *, item_id: int, affected_build: list[object] | None = None, assignee: object | None = None, deadline: object | None = None, desc: object | None = None, module: object | None = None, product: object | None = None, title: object | None = None, type: object | None = None) -> object | None:
        if product is None and module is None and title is None and type is None and desc is None and assignee is None and deadline is None and affected_build is None:
            raise UsageError("edit 至少需要提供一个修改字段")
        return self.api.edit(item_id=item_id, product=product, module=module, title=title, type=type, desc=desc, assignee=assignee, deadline=deadline, affected_build=affected_build)

    def list_product(self, *, product: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_product(product=product, browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def close(self, *, closed_reason: object | None, comment: object | None, item_id: int) -> object | None:
        return self.api.close(item_id=item_id, closed_reason=closed_reason, comment=comment)

    def activate(self, *, item_id: int, assignee: object | None = None, comment: object | None = None) -> object | None:
        return self.api.activate(item_id=item_id, assignee=assignee, comment=comment)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
