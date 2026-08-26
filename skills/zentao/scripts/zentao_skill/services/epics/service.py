from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.epics import EpicsAPI


class EpicsService:
    ENDPOINT_IDS = EpicsAPI.ENDPOINT_IDS

    def __init__(self, api: EpicsAPI) -> None:
        self.api = api

    def create(self, *, product: object | None, title: object | None, assignee: object | None = None, category: object | None = None, estimate: object | None = None, module: object | None = None, parent: object | None = None, priority: object | None = None, reviewer: list[object] | None = None, source: object | None = None, spec: object | None = None, verify: object | None = None) -> object | None:
        return self.api.create(product=product, title=title, priority=priority, module=module, parent=parent, estimate=estimate, spec=spec, category=category, source=source, verify=verify, assignee=assignee, reviewer=reviewer)

    def edit(self, *, item_id: int, title: object | None, assignee: object | None = None, category: object | None = None, estimate: object | None = None, module: object | None = None, parent: object | None = None, priority: object | None = None, reviewer: list[object] | None = None, source: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, title=title, priority=priority, module=module, parent=parent, estimate=estimate, category=category, source=source, assignee=assignee, reviewer=reviewer)

    def change(self, *, item_id: int, reviewer: list[object] | None, spec: object | None = None, title: object | None = None, verify: object | None = None) -> object | None:
        return self.api.change(item_id=item_id, title=title, reviewer=reviewer, spec=spec, verify=verify)

    def list_product(self, *, product: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_product(product=product, browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def close(self, *, closed_reason: object | None, item_id: int, comment: object | None = None, duplicate_story: object | None = None) -> object | None:
        return self.api.close(item_id=item_id, closed_reason=closed_reason, comment=comment, duplicate_story=duplicate_story)

    def activate(self, *, item_id: int, assignee: object | None = None, comment: object | None = None) -> object | None:
        return self.api.activate(item_id=item_id, assignee=assignee, comment=comment)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
