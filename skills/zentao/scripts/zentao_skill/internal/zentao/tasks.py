from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class TasksAPI:
    ENDPOINT_IDS = frozenset({'task.start', 'task.create', 'task.close', 'task.activate', 'task.delete', 'task.finish', 'task.list_execution', 'task.view', 'task.edit'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('task.create')
    def create(self, *, execution: object | None, name: object | None, assignee: object | None = None, deadline: object | None = None, desc: object | None = None, estimate: object | None = None, estimated_start: object | None = None, module: object | None = None, parent: object | None = None, priority: object | None = None, story: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'executionID': map_enum('executionID', execution),
            'type': map_enum('type', type),
            'assignedTo': map_enum('assignedTo', assignee),
            'estStarted': map_enum('estStarted', estimated_start),
            'deadline': map_enum('deadline', deadline),
            'pri': map_enum('pri', priority),
            'estimate': map_enum('estimate', estimate),
            'module': map_enum('module', module),
            'story': map_enum('story', story),
            'desc': map_enum('desc', desc),
            'parent': map_enum('parent', parent),
        })
        return self.session.post('/tasks', body=body)

    @endpoint('task.edit')
    def edit(self, *, item_id: int, assignee: object | None = None, deadline: object | None = None, desc: object | None = None, estimate: object | None = None, estimated_start: object | None = None, module: object | None = None, name: object | None = None, parent: object | None = None, priority: object | None = None, story: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'type': map_enum('type', type),
            'assignedTo': map_enum('assignedTo', assignee),
            'estStarted': map_enum('estStarted', estimated_start),
            'deadline': map_enum('deadline', deadline),
            'pri': map_enum('pri', priority),
            'estimate': map_enum('estimate', estimate),
            'module': map_enum('module', module),
            'story': map_enum('story', story),
            'desc': map_enum('desc', desc),
            'parent': map_enum('parent', parent),
        })
        return self.session.put(f'/tasks/{item_id}', body=body)

    @endpoint('task.list_execution')
    def list_execution(self, *, execution: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'browseType': map_enum('browseType', browse),
            'recPerPage': map_enum('recPerPage', per_page),
            'pageID': map_enum('pageID', page),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/executions/{execution}/tasks', query=query)

    @endpoint('task.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/tasks/{item_id}')

    @endpoint('task.start')
    def start(self, *, item_id: int, real_started: object | None, assignee: object | None = None, comment: object | None = None, consumed: object | None = None, left: object | None = None) -> object | None:
        body = compact_dict({
            'assignedTo': map_enum('assignedTo', assignee),
            'realStarted': map_enum('realStarted', real_started),
            'consumed': map_enum('consumed', consumed),
            'left': map_enum('left', left),
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/tasks/{item_id}/start', body=body)

    @endpoint('task.finish')
    def finish(self, *, current_consumed: object | None, finished_date: object | None, item_id: int, real_started: object | None, assignee: object | None = None, comment: object | None = None, consumed: object | None = None) -> object | None:
        body = compact_dict({
            'currentConsumed': map_enum('currentConsumed', current_consumed),
            'assignedTo': map_enum('assignedTo', assignee),
            'consumed': map_enum('consumed', consumed),
            'realStarted': map_enum('realStarted', real_started),
            'finishedDate': map_enum('finishedDate', finished_date),
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/tasks/{item_id}/finish', body=body)

    @endpoint('task.close')
    def close(self, *, item_id: int, comment: object | None = None) -> object | None:
        body = compact_dict({
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/tasks/{item_id}/close', body=body)

    @endpoint('task.activate')
    def activate(self, *, item_id: int, assignee: object | None = None, comment: object | None = None, left: object | None = None) -> object | None:
        body = compact_dict({
            'left': map_enum('left', left),
            'assignedTo': map_enum('assignedTo', assignee),
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/tasks/{item_id}/activate', body=body)

    @endpoint('task.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/tasks/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
