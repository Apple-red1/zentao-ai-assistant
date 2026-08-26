from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.test_cases import TestCasesAPI


class TestCasesService:
    ENDPOINT_IDS = TestCasesAPI.ENDPOINT_IDS

    def __init__(self, api: TestCasesAPI) -> None:
        self.api = api

    def create(self, *, product: object | None, title: object | None, execution: object | None = None, expect: list[object] | None = None, module: object | None = None, precondition: object | None = None, priority: object | None = None, project: object | None = None, step: list[object] | None = None, step_type: list[object] | None = None, story: object | None = None, type: object | None = None) -> object | None:
        return self.api.create(product=product, title=title, module=module, story=story, priority=priority, type=type, precondition=precondition, step=step, expect=expect, step_type=step_type, project=project, execution=execution)

    def edit(self, *, item_id: int, title: object | None, expect: list[object] | None = None, module: object | None = None, precondition: object | None = None, priority: object | None = None, step: list[object] | None = None, step_type: list[object] | None = None, story: object | None = None, type: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, title=title, module=module, story=story, priority=priority, type=type, precondition=precondition, step=step, expect=expect, step_type=step_type)

    def list_product(self, *, product: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_product(product=product, browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def list_project(self, *, project: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_project(project=project, browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def list_execution(self, *, execution: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_execution(execution=execution, browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
