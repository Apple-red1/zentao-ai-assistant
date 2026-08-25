from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class FeedbacksAPI:
    ENDPOINT_IDS = frozenset({'feedback.activate', 'feedback.list_product', 'feedback.delete', 'feedback.create', 'feedback.close', 'feedback.view', 'feedback.edit'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('feedback.create')
    def create(self, *, product: object | None, title: object | None, desc: object | None = None, feedback_by: object | None = None, module: object | None = None, source: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'product': map_enum('product', product),
            'title': map_enum('title', title),
            'module': map_enum('module', module),
            'type': map_enum('type', type),
            'desc': map_enum('desc', desc),
            'feedbackBy': map_enum('feedbackBy', feedback_by),
            'source': map_enum('source', source),
        })
        return self.session.post('/feedbacks', body=body)

    @endpoint('feedback.edit')
    def edit(self, *, item_id: int, product: object | None, title: object | None, desc: object | None = None, feedback_by: object | None = None, module: object | None = None, source: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'product': map_enum('product', product),
            'title': map_enum('title', title),
            'module': map_enum('module', module),
            'type': map_enum('type', type),
            'desc': map_enum('desc', desc),
            'feedbackBy': map_enum('feedbackBy', feedback_by),
            'source': map_enum('source', source),
        })
        return self.session.put(f'/feedbacks/{item_id}', body=body)

    @endpoint('feedback.list_product')
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
        return self.session.get(f'/products/{product}/feedbacks', query=query)

    @endpoint('feedback.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/feedbacks/{item_id}')

    @endpoint('feedback.close')
    def close(self, *, closed_reason: object | None, item_id: int, comment: object | None = None, confirm_close: object | None = None) -> object | None:
        body = compact_dict({
            'closedReason': map_enum('closedReason', closed_reason),
            'comment': map_enum('comment', comment),
            'confirmClose': map_enum('confirmClose', confirm_close),
        })
        return self.session.put(f'/feedbacks/{item_id}/close', body=body)

    @endpoint('feedback.activate')
    def activate(self, *, item_id: int, assignee: object | None = None, comment: object | None = None) -> object | None:
        body = compact_dict({
            'assignedTo': map_enum('assignedTo', assignee),
            'comment': map_enum('comment', comment),
        })
        return self.session.put(f'/feedbacks/{item_id}/activate', body=body)

    @endpoint('feedback.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/feedbacks/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
