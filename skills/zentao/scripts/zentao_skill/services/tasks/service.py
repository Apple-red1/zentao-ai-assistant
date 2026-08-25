from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.tasks import TasksAPI


class TasksService:
    ENDPOINT_IDS = TasksAPI.ENDPOINT_IDS

    def __init__(self, api: TasksAPI) -> None:
        self.api = api

    def create(self, *, execution: object | None, name: object | None, assignee: object | None = None, deadline: object | None = None, desc: object | None = None, estimate: object | None = None, estimated_start: object | None = None, module: object | None = None, parent: object | None = None, priority: object | None = None, story: object | None = None, type: object | None = None) -> object | None:
        return self.api.create(name=name, execution=execution, type=type, assignee=assignee, estimated_start=estimated_start, deadline=deadline, priority=priority, estimate=estimate, module=module, story=story, desc=desc, parent=parent)

    def edit(self, *, item_id: int, assignee: object | None = None, deadline: object | None = None, desc: object | None = None, estimate: object | None = None, estimated_start: object | None = None, module: object | None = None, name: object | None = None, parent: object | None = None, priority: object | None = None, story: object | None = None, type: object | None = None) -> object | None:
        if name is None and type is None and assignee is None and estimated_start is None and deadline is None and priority is None and estimate is None and module is None and story is None and desc is None and parent is None:
            raise UsageError("edit 至少需要提供一个修改字段")
        return self.api.edit(item_id=item_id, name=name, type=type, assignee=assignee, estimated_start=estimated_start, deadline=deadline, priority=priority, estimate=estimate, module=module, story=story, desc=desc, parent=parent)

    def list_execution(self, *, execution: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list_execution(execution=execution, browse=browse, sort=sort, order=order, per_page=per_page, page=page)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def start(self, *, item_id: int, real_started: object | None, assignee: object | None = None, comment: object | None = None, consumed: object | None = None, left: object | None = None) -> object | None:
        return self.api.start(item_id=item_id, assignee=assignee, real_started=real_started, consumed=consumed, left=left, comment=comment)

    def finish(self, *, current_consumed: object | None, finished_date: object | None, item_id: int, real_started: object | None, assignee: object | None = None, comment: object | None = None, consumed: object | None = None) -> object | None:
        return self.api.finish(item_id=item_id, current_consumed=current_consumed, assignee=assignee, consumed=consumed, real_started=real_started, finished_date=finished_date, comment=comment)

    def close(self, *, item_id: int, comment: object | None = None) -> object | None:
        return self.api.close(item_id=item_id, comment=comment)

    def activate(self, *, item_id: int, assignee: object | None = None, comment: object | None = None, left: object | None = None) -> object | None:
        return self.api.activate(item_id=item_id, left=left, assignee=assignee, comment=comment)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
