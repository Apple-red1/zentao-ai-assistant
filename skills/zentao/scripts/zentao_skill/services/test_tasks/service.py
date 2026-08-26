from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.test_tasks import TestTasksAPI


class TestTasksService:
    ENDPOINT_IDS = TestTasksAPI.ENDPOINT_IDS

    def __init__(self, api: TestTasksAPI) -> None:
        self.api = api

    def create(self, *, begin: object | None, build: object | None, end: object | None, name: object | None, product: object | None, desc: object | None = None, execution: object | None = None, owner: object | None = None, status: object | None = None, type: list[object] | None = None) -> object | None:
        return self.api.create(product=product, name=name, build=build, execution=execution, type=type, owner=owner, status=status, begin=begin, end=end, desc=desc)

    def edit(self, *, begin: object | None, build: object | None, end: object | None, item_id: int, name: object | None, desc: object | None = None, execution: object | None = None, owner: object | None = None, status: object | None = None, type: list[object] | None = None) -> object | None:
        return self.api.edit(item_id=item_id, name=name, build=build, execution=execution, type=type, owner=owner, status=status, begin=begin, end=end, desc=desc)

    def list_product(self, *, product: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_product(product=product, browse=browse, sort=sort, order=order, per_page=per_page, page=page)

    def list_project(self, *, project: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_project(project=project, browse=browse, sort=sort, order=order, per_page=per_page, page=page)

    def list_execution(self, *, execution: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_execution(execution=execution, browse=browse, sort=sort, order=order, per_page=per_page, page=page)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
