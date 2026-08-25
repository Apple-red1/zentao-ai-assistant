from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.projects import ProjectsAPI


class ProjectsService:
    ENDPOINT_IDS = ProjectsAPI.ENDPOINT_IDS

    def __init__(self, api: ProjectsAPI) -> None:
        self.api = api

    def create(self, *, begin: object | None, end: object | None, model: object | None, name: object | None, parent: object | None = None, pm: object | None = None, product: list[object] | None = None, workflow_group: object | None = None) -> object | None:
        return self.api.create(name=name, model=model, begin=begin, end=end, product=product, parent=parent, workflow_group=workflow_group, pm=pm)

    def edit(self, *, begin: object | None, end: object | None, item_id: int, model: object | None, name: object | None, parent: object | None = None, pm: object | None = None, product: list[object] | None = None, workflow_group: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, name=name, model=model, begin=begin, end=end, product=product, parent=parent, workflow_group=workflow_group, pm=pm)

    def list(self, *, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list(browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def list_program(self, *, program: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_program(program=program, browse=browse, sort=sort, order=order, per_page=per_page, page=page)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
