from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class RequirementsAPI:
    ENDPOINT_IDS = frozenset({'requirement.create', 'requirement.close', 'requirement.activate', 'requirement.delete', 'requirement.edit', 'requirement.list_product', 'requirement.view', 'requirement.change'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('requirement.create')
    def create(self, *, product: object | None, title: object | None, assignee: object | None = None, category: object | None = None, estimate: object | None = None, module: object | None = None, parent: object | None = None, priority: object | None = None, reviewer: list[object] | None = None, source: object | None = None, spec: object | None = None, verify: object | None = None) -> object | None:
        body = compact_dict({
            'productID': map_enum('productID', product),
            'title': map_enum('title', title),
            'pri': map_enum('pri', priority),
            'module': map_enum('module', module),
            'parent': map_enum('parent', parent),
            'estimate': map_enum('estimate', estimate),
            'spec': map_enum('spec', spec),
            'category': map_enum('category', category),
            'source': map_enum('source', source),
            'verify': map_enum('verify', verify),
            'assignedTo': map_enum('assignedTo', assignee),
            'reviewer': map_enum('reviewer', reviewer),
        })
        return self.session.post('/requirements', body=body)

    @endpoint('requirement.edit')
    def edit(self, *, item_id: int, title: object | None, assignee: object | None = None, category: object | None = None, estimate: object | None = None, module: object | None = None, parent: object | None = None, priority: object | None = None, reviewer: list[object] | None = None, source: object | None = None) -> object | None:
        body = compact_dict({
            'title': map_enum('title', title),
            'pri': map_enum('pri', priority),
            'module': map_enum('module', module),
            'parent': map_enum('parent', parent),
            'estimate': map_enum('estimate', estimate),
            'category': map_enum('category', category),
            'source': map_enum('source', source),
            'assignedTo': map_enum('assignedTo', assignee),
            'reviewer': map_enum('reviewer', reviewer),
        })
        return self.session.put(f'/requirements/{item_id}', body=body)

    @endpoint('requirement.change')
    def change(self, *, item_id: int, reviewer: list[object] | None, spec: object | None = None, title: object | None = None, verify: object | None = None) -> object | None:
        body = compact_dict({
            'title': map_enum('title', title),
            'reviewer': map_enum('reviewer', reviewer),
            'spec': map_enum('spec', spec),
            'verify': map_enum('verify', verify),
        })
        return self.session.put(f'/requirements/{item_id}/change', body=body)

    @endpoint('requirement.list_product')
    def list_product(self, *, product: int, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        validate_pagination(page if "page" in locals() else None, per_page if "per_page" in locals() else None)
        query = compact_dict({
            'browseType': map_enum('browseType', browse),
            'recPerPage': map_enum('recPerPage', per_page),
            'pageID': map_enum('pageID', page),
            'filters': map_enum('filters', filters),
            'groupJoin': map_enum('groupJoin', group_join),
        })
        if order is not None and sort is None:
            raise UsageError('--order 只能与 --sort 一起使用')
        if sort is not None:
            query['orderBy'] = make_order_by(sort, order)
        return self.session.get(f'/products/{product}/requirements', query=query)

    @endpoint('requirement.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/requirements/{item_id}')

    @endpoint('requirement.close')
    def close(self, *, closed_reason: object | None, item_id: int, comment: object | None = None, duplicate_story: object | None = None) -> object | None:
        body = compact_dict({
            'closedReason': map_enum('closedReason', closed_reason),
            'comment': map_enum('comment', comment),
            'duplicateStory': map_enum('duplicateStory', duplicate_story),
        })
        return self.session.put(f'/requirements/{item_id}/close', body=body)

    @endpoint('requirement.activate')
    def activate(self, *, item_id: int, assignee: object | None = None, comment: object | None = None) -> object | None:
        body = compact_dict({
            'assignedTo': map_enum('assignedTo', assignee),
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/requirements/{item_id}/activate', body=body)

    @endpoint('requirement.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/requirements/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
