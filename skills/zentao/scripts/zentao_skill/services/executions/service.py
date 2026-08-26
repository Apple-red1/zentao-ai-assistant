from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.executions import ExecutionsAPI


class ExecutionsService:
    ENDPOINT_IDS = ExecutionsAPI.ENDPOINT_IDS

    def __init__(self, api: ExecutionsAPI) -> None:
        self.api = api

    def create(self, *, begin: object | None, end: object | None, name: object | None, product: list[object] | None, project: object | None, acl: object | None = None, attribute: object | None = None, days: object | None = None, lifetime: object | None = None, milestone: object | None = None, parent: object | None = None, plan: list[object] | None = None, pm: object | None = None, po: object | None = None, qd: object | None = None, rd: object | None = None, type: object | None = None) -> object | None:
        return self.api.create(project=project, name=name, type=type, parent=parent, attribute=attribute, lifetime=lifetime, begin=begin, end=end, days=days, product=product, plan=plan, po=po, qd=qd, pm=pm, rd=rd, acl=acl, milestone=milestone)

    def edit(self, *, begin: object | None, end: object | None, item_id: int, name: object | None, acl: object | None = None, days: object | None = None, lifetime: object | None = None, plan: list[object] | None = None, pm: object | None = None, po: object | None = None, product: list[object] | None = None, project: object | None = None, qd: object | None = None, rd: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, name=name, begin=begin, end=end, project=project, lifetime=lifetime, days=days, product=product, plan=plan, po=po, qd=qd, pm=pm, rd=rd, acl=acl)

    def list(self, *, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list(browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def list_project(self, *, project: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_project(project=project, browse=browse, sort=sort, order=order, per_page=per_page, page=page)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
