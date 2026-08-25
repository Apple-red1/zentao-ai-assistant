from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class BugsAPI:
    ENDPOINT_IDS = frozenset({'bug.create', 'bug.list_project', 'bug.activate', 'bug.delete', 'bug.edit', 'bug.list_execution', 'bug.list_product', 'bug.resolve', 'bug.close', 'bug.view'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('bug.create')
    def create(self, *, affected_build: list[object] | None, product: object | None, title: object | None, assignee: object | None = None, branch: object | None = None, browser: object | None = None, deadline: object | None = None, execution: object | None = None, keywords: object | None = None, module: object | None = None, os: object | None = None, priority: object | None = None, project: object | None = None, severity: object | None = None, steps: object | None = None, story: object | None = None, task: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'productID': map_enum('productID', product),
            'title': map_enum('title', title),
            'openedBuild': map_enum('openedBuild', affected_build),
            'branch': map_enum('branch', branch),
            'module': map_enum('module', module),
            'project': map_enum('project', project),
            'execution': map_enum('execution', execution),
            'story': map_enum('story', story),
            'task': map_enum('task', task),
            'severity': map_enum('severity', severity),
            'pri': map_enum('pri', priority),
            'type': map_enum('type', type),
            'os': map_enum('os', os),
            'browser': map_enum('browser', browser),
            'steps': map_enum('steps', steps),
            'assignedTo': map_enum('assignedTo', assignee),
            'deadline': map_enum('deadline', deadline),
            'keywords': map_enum('keywords', keywords),
        })
        return self.session.post('/bugs', body=body)

    @endpoint('bug.edit')
    def edit(self, *, item_id: int, affected_build: list[object] | None = None, assignee: object | None = None, execution: object | None = None, priority: object | None = None, project: object | None = None, severity: object | None = None, steps: object | None = None, story: object | None = None, title: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'title': map_enum('title', title),
            'severity': map_enum('severity', severity),
            'pri': map_enum('pri', priority),
            'type': map_enum('type', type),
            'openedBuild': map_enum('openedBuild', affected_build),
            'steps': map_enum('steps', steps),
            'project': map_enum('project', project),
            'execution': map_enum('execution', execution),
            'story': map_enum('story', story),
            'assignedTo': map_enum('assignedTo', assignee),
        })
        return self.session.put(f'/bugs/{item_id}', body=body)

    @endpoint('bug.list_product')
    def list_product(self, *, product: int, branch: object | None = None, browse: object | None = None, filters: object | None = None, group_join: object | None = None, module: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'branch': map_enum('branch', branch),
            'browseType': map_enum('browseType', browse),
            'module': map_enum('module', module),
            'pageID': map_enum('pageID', page),
            'recPerPage': map_enum('recPerPage', per_page),
            'filters': map_enum('filters', filters),
            'groupJoin': map_enum('groupJoin', group_join),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/products/{product}/bugs', query=query)

    @endpoint('bug.list_project')
    def list_project(self, *, project: int, browse: object | None = None, execution_filter: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, param: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'executionID': map_enum('executionID', execution_filter),
            'browseType': map_enum('browseType', browse),
            'param': map_enum('param', param),
            'pageID': map_enum('pageID', page),
            'recPerPage': map_enum('recPerPage', per_page),
            'filters': map_enum('filters', filters),
            'groupJoin': map_enum('groupJoin', group_join),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/projects/{project}/bugs', query=query)

    @endpoint('bug.list_execution')
    def list_execution(self, *, execution: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, param: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'browseType': map_enum('browseType', browse),
            'param': map_enum('param', param),
            'pageID': map_enum('pageID', page),
            'recPerPage': map_enum('recPerPage', per_page),
            'filters': map_enum('filters', filters),
            'groupJoin': map_enum('groupJoin', group_join),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/executions/{execution}/bugs', query=query)

    @endpoint('bug.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/bugs/{item_id}')

    @endpoint('bug.resolve')
    def resolve(self, *, item_id: int, resolution: object | None, assignee: object | None = None, comment: object | None = None, duplicate_bug: object | None = None, resolved_build: object | None = None, resolved_date: object | None = None) -> object | None:
        body = compact_dict({
            'resolution': map_enum('resolution', resolution),
            'resolvedDate': map_enum('resolvedDate', resolved_date),
            'resolvedBuild': map_enum('resolvedBuild', resolved_build),
            'duplicateBug': map_enum('duplicateBug', duplicate_bug),
            'assignedTo': map_enum('assignedTo', assignee),
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/bugs/{item_id}/resolve', body=body)

    @endpoint('bug.close')
    def close(self, *, item_id: int, comment: object | None = None) -> object | None:
        body = compact_dict({
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/bugs/{item_id}/close', body=body)

    @endpoint('bug.activate')
    def activate(self, *, item_id: int, affected_build: list[object] | None = None, assignee: object | None = None, comment: object | None = None) -> object | None:
        body = compact_dict({
            'openedBuild': map_enum('openedBuild', affected_build),
            'assignedTo': map_enum('assignedTo', assignee),
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/bugs/{item_id}/activate', body=body)

    @endpoint('bug.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/bugs/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
