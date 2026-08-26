from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.builds import BuildsAPI


class BuildsService:
    ENDPOINT_IDS = BuildsAPI.ENDPOINT_IDS

    def __init__(self, api: BuildsAPI) -> None:
        self.api = api

    def create(self, *, builder: object | None, date: object | None, execution: object | None, name: object | None, product: object | None, system: object | None, desc: object | None = None, file_path: object | None = None, scm_path: object | None = None) -> object | None:
        return self.api.create(execution=execution, product=product, name=name, system=system, builder=builder, date=date, scm_path=scm_path, file_path=file_path, desc=desc)

    def edit(self, *, builder: object | None, date: object | None, execution: object | None, item_id: int, name: object | None, product: object | None, system: object | None, desc: object | None = None, file_path: object | None = None, scm_path: object | None = None) -> object | None:
        return self.api.edit(item_id=item_id, execution=execution, product=product, name=name, system=system, builder=builder, date=date, scm_path=scm_path, file_path=file_path, desc=desc)

    def list_project(self, *, project: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_project(project=project, browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def list_execution(self, *, execution: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_execution(execution=execution, browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
