from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


def normalize_plans(plans: object | None, products: list[object] | None = None) -> object | None:
    """Convert repeatable CLI plan values to ZenTao's product-keyed object."""
    if plans is None:
        return None
    values = plans if isinstance(plans, list) else [plans]
    result: dict[str, list[object]] = {}
    default_product = str(products[0]) if products and len(products) == 1 else None
    for value in values:
        if isinstance(value, dict):
            if "product" in value and "plan" in value:
                result.setdefault(str(value["product"]), []).append(value["plan"])
                continue
            for product, plan_ids in value.items():
                ids = plan_ids if isinstance(plan_ids, list) else [plan_ids]
                result.setdefault(str(product), []).extend(ids)
            continue
        if default_product is None:
            raise UsageError("--plan 使用纯 ID 时必须只指定一个 --product")
        result.setdefault(default_product, []).append(value)
    return result


class ExecutionsAPI:
    ENDPOINT_IDS = frozenset({'execution.edit', 'execution.view', 'execution.list', 'execution.list_project', 'execution.create', 'execution.delete'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('execution.create')
    def create(self, *, begin: object | None, end: object | None, name: object | None, product: list[object] | None, project: object | None, acl: object | None = None, attribute: object | None = None, days: object | None = None, lifetime: object | None = None, milestone: object | None = None, parent: object | None = None, plan: list[object] | None = None, pm: object | None = None, po: object | None = None, qd: object | None = None, rd: object | None = None, type: object | None = None) -> object | None:
        body = compact_dict({
            'project': map_enum('project', project),
            'name': map_enum('name', name),
            'type': map_enum('type', type),
            'parent': map_enum('parent', parent),
            'attribute': map_enum('attribute', attribute),
            'lifetime': map_enum('lifetime', lifetime),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'days': map_enum('days', days),
            'products': map_enum('products', product),
            'plans': normalize_plans(plan, product),
            'PO': map_enum('PO', po),
            'QD': map_enum('QD', qd),
            'PM': map_enum('PM', pm),
            'RD': map_enum('RD', rd),
            'acl': map_enum('acl', acl),
            'milestone': map_enum('milestone', milestone),
        })
        return self.session.post('/executions', body=body)

    @endpoint('execution.edit')
    def edit(self, *, begin: object | None, end: object | None, item_id: int, name: object | None, acl: object | None = None, days: object | None = None, lifetime: object | None = None, plan: list[object] | None = None, pm: object | None = None, po: object | None = None, product: list[object] | None = None, project: object | None = None, qd: object | None = None, rd: object | None = None) -> object | None:
        body = compact_dict({
            'name': map_enum('name', name),
            'begin': map_enum('begin', begin),
            'end': map_enum('end', end),
            'project': map_enum('project', project),
            'lifetime': map_enum('lifetime', lifetime),
            'days': map_enum('days', days),
            'products': map_enum('products', product),
            'plans': normalize_plans(plan, product),
            'PO': map_enum('PO', po),
            'QD': map_enum('QD', qd),
            'PM': map_enum('PM', pm),
            'RD': map_enum('RD', rd),
            'acl': map_enum('acl', acl),
        })
        return self.session.put(f'/executions/{item_id}', body=body)

    @endpoint('execution.list')
    def list(self, *, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
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
        return self.session.get('/executions', query=query)

    @endpoint('execution.list_project')
    def list_project(self, *, project: int, browse: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
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
        return self.session.get(f'/projects/{project}/executions', query=query)

    @endpoint('execution.view')
    def view(self, *, item_id: int) -> object | None:
        return self.session.get(f'/executions/{item_id}')

    @endpoint('execution.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/executions/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
