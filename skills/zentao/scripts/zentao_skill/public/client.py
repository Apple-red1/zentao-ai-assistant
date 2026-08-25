from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..internal.errors import ApiError, UsageError
from ..services.container import Services


_LIST_ACTIONS: dict[str, dict[str | None, str]] = {
    "bug": {"product": "list_product", "project": "list_project", "execution": "list_execution"},
    "task": {"execution": "list_execution"},
    "story": {"product": "list_product", "project": "list_project", "execution": "list_execution"},
    "requirement": {"product": "list_product"},
    "test-case": {"product": "list_product", "project": "list_project", "execution": "list_execution"},
    "test-task": {"product": "list_product", "project": "list_project", "execution": "list_execution"},
    "ticket": {"product": "list_product"},
    "feedback": {"product": "list_product"},
    "product": {None: "list", "program": "list_program"},
    "project": {None: "list", "program": "list_program"},
    "execution": {None: "list", "project": "list_project"},
    "build": {"project": "list_project", "execution": "list_execution"},
    "release": {"product": "list_product"},
    "user": {None: "list"},
}

_VIEW_RESOURCES = frozenset({
    "bug", "task", "story", "requirement", "test-case", "ticket", "feedback", "product", "execution", "user"
})

_READ_ACTIONS: dict[str, frozenset[str]] = {
    resource: frozenset(set(actions.values()) | ({"view"} if resource in _VIEW_RESOURCES else set()))
    for resource, actions in _LIST_ACTIONS.items()
}

_COLLECTION_KEYS = {
    "bug": "bugs", "task": "tasks", "story": "stories", "requirement": "requirements",
    "test-case": "testcases", "test-task": "testtasks", "ticket": "tickets", "feedback": "feedbacks",
    "product": "products", "project": "projects", "execution": "executions", "build": "builds",
    "release": "releases", "user": "users",
}


@dataclass(frozen=True)
class ListResult:
    items: list[dict[str, Any]]
    complete: bool
    pages: int
    total: int | None
    partial_failures: list[dict[str, object]]


class ZentaoClient:
    """Stable programmatic facade for repository-owned higher-level ZenTao Skills."""

    def __init__(self, *, services: Services | None = None) -> None:
        self.services = services or Services()

    @property
    def account(self) -> str:
        session = getattr(self.services, "session", None)
        config = getattr(session, "config", None)
        return str(getattr(config, "account", ""))

    def call(self, resource: str, action: str, **kwargs: object) -> object | None:
        allowed = _READ_ACTIONS.get(resource, frozenset())
        if action not in allowed:
            raise UsageError(f"程序化 facade 仅允许只读操作: {resource}.{action}")
        service = self._service(resource)
        method = getattr(service, action, None)
        if method is None or action.startswith("_"):
            raise UsageError(f"不支持的程序化操作: {resource}.{action}")
        return method(**kwargs)

    def list_page(self, resource: str, *, scope: str | None = None, scope_id: int | None = None,
                  page: int = 1, per_page: int = 1000, browse: str | None = None) -> dict[str, Any]:
        actions = _LIST_ACTIONS.get(resource)
        if actions is None or scope not in actions:
            raise UsageError(f"{resource} 不支持 scope={scope or 'global'} 的列表读取")
        if scope is not None and (scope_id is None or scope_id <= 0):
            raise UsageError("scope id 必须是正整数")
        kwargs: dict[str, object] = {"page": page, "per_page": per_page}
        if scope is not None:
            kwargs[scope] = scope_id
        if browse is not None:
            kwargs["browse"] = browse
        payload = self.call(resource, actions[scope], **kwargs)
        if not isinstance(payload, dict):
            raise ApiError("ZenTao 列表响应不是对象", {"resource": resource})
        return payload

    def list_all(self, resource: str, *, scope: str | None = None, scope_id: int | None = None,
                 per_page: int = 1000, browse: str | None = None, max_pages: int = 10000) -> ListResult:
        if per_page < 1 or per_page > 1000:
            raise UsageError("per_page 必须在 1..1000")
        collection_key = _COLLECTION_KEYS.get(resource)
        if collection_key is None:
            raise UsageError(f"不支持的聚合资源: {resource}")
        items: list[dict[str, Any]] = []
        partial_failures: list[dict[str, object]] = []
        total: int | None = None
        seen_ids: set[str] = set()
        page = 1
        while page <= max_pages:
            payload = self.list_page(resource, scope=scope, scope_id=scope_id, page=page, per_page=per_page, browse=browse)
            rows = payload.get(collection_key)
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise ApiError("ZenTao 列表响应缺少合法集合", {"resource": resource, "field": collection_key})
            before_seen = len(seen_ids)
            page_has_only_ids = bool(rows) and all(row.get("id") is not None for row in rows)
            if page_has_only_ids:
                seen_ids.update(str(row["id"]) for row in rows)
            items.extend(rows)
            pager = payload.get("pager")
            if isinstance(pager, dict):
                raw_total = pager.get("total")
                if isinstance(raw_total, int):
                    total = raw_total
                elif isinstance(raw_total, str) and raw_total.isdigit():
                    total = int(raw_total)
            received = len(seen_ids) if seen_ids and all(row.get("id") is not None for row in items) else len(items)
            if total is not None and received >= total:
                return ListResult(items=items, complete=True, pages=page, total=total, partial_failures=partial_failures)
            if not rows or (page_has_only_ids and len(seen_ids) == before_seen):
                complete = total is None and not rows
                if not complete:
                    partial_failures.append({"code": "PAGINATION_STALLED", "page": page, "expected_total": total, "received": received})
                return ListResult(items=items, complete=complete, pages=page, total=total, partial_failures=partial_failures)
            if len(rows) < per_page and total is None:
                return ListResult(items=items, complete=True, pages=page, total=received, partial_failures=partial_failures)
            page += 1
        partial_failures.append({"code": "MAX_PAGES_REACHED", "max_pages": max_pages})
        return ListResult(items=items, complete=False, pages=max_pages, total=total, partial_failures=partial_failures)

    def view(self, resource: str, item_id: int) -> object | None:
        if item_id <= 0:
            raise UsageError("id 必须是正整数")
        return self.call(resource, "view", item_id=item_id)

    def _service(self, resource: str) -> object:
        attr = resource.replace("-", "_")
        service = getattr(self.services, attr, None)
        if service is None:
            raise UsageError(f"不支持的资源: {resource}")
        return service
