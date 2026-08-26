from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, require_response_body, require_success_field, validate_pagination
from .session import ZentaoSession


class TicketsAPI:
    ENDPOINT_IDS = frozenset({'ticket.close', 'ticket.view', 'ticket.delete', 'ticket.create', 'ticket.activate', 'ticket.list_product', 'ticket.edit'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('ticket.create')
    def create(self, *, product: object | None, title: object | None, affected_build: list[object] | None = None, assignee: object | None = None, deadline: object | None = None, desc: object | None = None, module: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'product': map_enum('product', product),
            'module': map_enum('module', module),
            'title': map_enum('title', title),
            'type': map_enum('type', type),
            'desc': map_enum('desc', desc),
            'assignedTo': map_enum('assignedTo', assignee),
            'deadline': map_enum('deadline', deadline),
            'openedBuild': map_enum('openedBuild', affected_build),
        })
        return require_success_field(self.session.post('/tickets', body=body), endpoint_id='ticket.create', field='id', feature='工单')

    @endpoint('ticket.edit')
    def edit(self, *, item_id: int, affected_build: list[object] | None = None, assignee: object | None = None, deadline: object | None = None, desc: object | None = None, module: object | None = None, product: object | None = None, title: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'product': map_enum('product', product),
            'module': map_enum('module', module),
            'title': map_enum('title', title),
            'type': map_enum('type', type),
            'desc': map_enum('desc', desc),
            'assignedTo': map_enum('assignedTo', assignee),
            'deadline': map_enum('deadline', deadline),
            'openedBuild': map_enum('openedBuild', affected_build),
        })
        return require_response_body(self.session.put(f'/tickets/{item_id}', body=body), endpoint_id='ticket.edit', feature='工单编辑')

    @endpoint('ticket.list_product')
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
        return require_success_field(self.session.get(f'/products/{product}/tickets', query=query), endpoint_id='ticket.list_product', field='tickets', feature='工单')

    @endpoint('ticket.view')
    def view(self, *, item_id: int) -> object | None:
        return require_success_field(self.session.get(f'/tickets/{item_id}'), endpoint_id='ticket.view', field='ticket', feature='工单')

    @endpoint('ticket.close')
    def close(self, *, closed_reason: object | None, comment: object | None, item_id: int) -> object | None:
        body = compact_dict({
            'closedReason': map_enum('closedReason', closed_reason),
            'comment': map_enum('comment', comment),
        })
        return require_response_body(self.session.put(f'/tickets/{item_id}/close', body=body), endpoint_id='ticket.close', feature='工单关闭')

    @endpoint('ticket.activate')
    def activate(self, *, item_id: int, assignee: object | None = None, comment: object | None = None) -> object | None:
        body = compact_dict({
            'assignedTo': map_enum('assignedTo', assignee),
            'comment': map_enum('comment', comment),
        })
        return require_response_body(self.session.put(f'/tickets/{item_id}/activate', body=body), endpoint_id='ticket.activate', feature='工单激活')

    @endpoint('ticket.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/tickets/{item_id}')
        return result if result is not None else {'status': 'success', 'id': item_id}
