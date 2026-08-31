from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.bugs import BugsAPI


class BugsService:
    ENDPOINT_IDS = BugsAPI.ENDPOINT_IDS

    def __init__(self, api: BugsAPI) -> None:
        self.api = api

    def create(self, *, affected_build: list[object] | None, product: object | None, title: object | None, assignee: object | None = None, branch: object | None = None, browser: object | None = None, deadline: object | None = None, execution: object | None = None, keywords: object | None = None, module: object | None = None, os: object | None = None, priority: object | None = None, project: object | None = None, severity: object | None = None, steps: object | None = None, steps_inline_images: list[str] | None = None, story: object | None = None, task: object | None = None, type: object | None = None) -> object | None:
        return self.api.create(product=product, title=title, affected_build=affected_build, branch=branch, module=module, project=project, execution=execution, story=story, task=task, severity=severity, priority=priority, type=type, os=os, browser=browser, steps=steps, steps_inline_images=steps_inline_images or (), assignee=assignee, deadline=deadline, keywords=keywords)

    def edit(self, *, item_id: int, affected_build: list[object] | None = None, execution: object | None = None, priority: object | None = None, project: object | None = None, severity: object | None = None, steps: object | None = None, steps_inline_images: list[str] | None = None, story: object | None = None, title: object | None = None, type: object | None = None) -> object | None:
        if title is None and severity is None and priority is None and type is None and affected_build is None and steps is None and not steps_inline_images and project is None and execution is None and story is None:
            raise UsageError("edit 至少需要提供一个修改字段")
        return self.api.edit(item_id=item_id, title=title, severity=severity, priority=priority, type=type, affected_build=affected_build, steps=steps, steps_inline_images=steps_inline_images or (), project=project, execution=execution, story=story)

    def list_product(self, *, product: int, branch: object | None = None, browse: object | None = None, filters: object | None = None, group_join: object | None = None, module: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_product(product=product, branch=branch, browse=browse, module=module, sort=sort, order=order, page=page, per_page=per_page, filters=filters, group_join=group_join)

    def list_project(self, *, project: int, browse: object | None = None, execution_filter: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, param: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_project(project=project, execution_filter=execution_filter, browse=browse, param=param, sort=sort, order=order, page=page, per_page=per_page, filters=filters, group_join=group_join)

    def list_execution(self, *, execution: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, param: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_execution(execution=execution, browse=browse, param=param, sort=sort, order=order, page=page, per_page=per_page, filters=filters, group_join=group_join)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def resolve(self, *, item_id: int, resolution: object | None, assignee: object | None = None, comment: object | None = None, duplicate_bug: object | None = None, resolved_build: object | None = None, resolved_date: object | None = None) -> object | None:
        if resolution == "duplicate" and duplicate_bug is None:
            raise UsageError("resolution=duplicate 时必须提供 --duplicate-bug")
        return self.api.resolve(item_id=item_id, resolution=resolution, resolved_date=resolved_date, resolved_build=resolved_build, duplicate_bug=duplicate_bug, assignee=assignee, comment=comment)

    def close(self, *, item_id: int, comment: object | None = None) -> object | None:
        return self.api.close(item_id=item_id, comment=comment)

    def activate(self, *, item_id: int, affected_build: list[object] | None = None, assignee: object | None = None, comment: object | None = None) -> object | None:
        return self.api.activate(item_id=item_id, affected_build=affected_build, assignee=assignee, comment=comment)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
