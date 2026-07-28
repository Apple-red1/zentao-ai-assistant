from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol

from zentao_ai.errors import ErrorCode, ZentaoError
from zentao_ai.models import (
    BugFilters,
    BugQueryResult,
    BugRecord,
    BugSummary,
    Settings,
    UserRef,
)

QueryValue = str | int | float | bool | None


class JsonClient(Protocol):
    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryValue] | None = None,
        json: Mapping[str, object] | None = None,
        write: bool = False,
    ) -> dict[str, Any]: ...


def _matches(value: int | str | None, allowed: Sequence[int | str]) -> bool:
    if not allowed:
        return True
    return str(value) in {str(item) for item in allowed}


def apply_filters(bugs: list[BugRecord], filters: BugFilters) -> list[BugRecord]:
    result: list[BugRecord] = []
    assigned = set(filters.assigned_to)
    opened_by = set(filters.opened_by)
    bug_types = {item.casefold() for item in filters.bug_type}
    keyword = filters.keyword.casefold() if filters.keyword else None

    for bug in bugs:
        if filters.status == "unresolved" and bug.status.casefold() in {"resolved", "closed"}:
            continue
        if filters.status not in {"unresolved", "all"} and bug.status != filters.status:
            continue
        if assigned and bug.assigned_to not in assigned:
            continue
        if opened_by and bug.opened_by not in opened_by:
            continue
        if filters.product_id is not None and bug.product_id != filters.product_id:
            continue
        if filters.project_id is not None and bug.project_id != filters.project_id:
            continue
        if filters.execution_id is not None and bug.execution_id != filters.execution_id:
            continue
        if not _matches(bug.priority, filters.priority):
            continue
        if not _matches(bug.severity, filters.severity):
            continue
        if bug_types and bug.bug_type.casefold() not in bug_types:
            continue
        if keyword and keyword not in f"{bug.title}\n{bug.steps}".casefold():
            continue
        if filters.opened_after and (not bug.opened_at or bug.opened_at < filters.opened_after):
            continue
        if filters.opened_before and (not bug.opened_at or bug.opened_at > filters.opened_before):
            continue
        if filters.edited_after and (not bug.edited_at or bug.edited_at < filters.edited_after):
            continue
        if filters.edited_before and (not bug.edited_at or bug.edited_at > filters.edited_before):
            continue
        result.append(bug)

    reverse = filters.order_by.startswith("-")
    field = filters.order_by.removeprefix("-")

    def sort_key(bug: BugRecord) -> tuple[bool, object, int]:
        value: object = getattr(bug, field)
        if field in {"priority", "severity"}:
            try:
                value = int(str(value))
            except (TypeError, ValueError):
                value = str(value or "")
        return (value is None, value or 0, bug.id)

    return sorted(result, key=sort_key, reverse=reverse)


def summarize_bugs(bugs: list[BugRecord]) -> BugSummary:
    def stable(counter: Counter[str]) -> dict[str, int]:
        return {key: counter[key] for key in sorted(counter)}

    return BugSummary(
        total=len(bugs),
        by_status=stable(Counter(bug.status or "unknown" for bug in bugs)),
        by_assignee=stable(Counter(bug.assigned_to or "unassigned" for bug in bugs)),
        by_priority=stable(Counter(str(bug.priority or "unset") for bug in bugs)),
        by_severity=stable(Counter(str(bug.severity or "unset") for bug in bugs)),
    )


class BugService:
    def __init__(self, client: JsonClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def get_bug(self, bug_id: int) -> BugRecord:
        if bug_id <= 0:
            raise ZentaoError(ErrorCode.VALIDATION_ERROR, "Bug ID must be positive.")
        payload = await self._client.request_json("GET", f"/bugs/{bug_id}")
        raw = payload.get("bug") or payload.get("data") or payload
        if not isinstance(raw, Mapping) or not raw.get("id"):
            raise ZentaoError(ErrorCode.BUG_NOT_FOUND, f"Bug {bug_id} was not found.")
        return parse_bug(raw)

    async def query_my_bugs(self, filters: BugFilters | None = None) -> BugQueryResult:
        selected = filters or BugFilters()
        selected = selected.model_copy(
            update={"assigned_to": [self._settings.zentao.account]},
        )
        return await self.search_bugs(selected)

    async def query_user_bugs(
        self,
        user: UserRef,
        filters: BugFilters | None = None,
    ) -> BugQueryResult:
        selected = (filters or BugFilters()).model_copy(
            update={"assigned_to": [user.account]},
        )
        return await self.search_bugs(selected)

    async def query_team_bugs(
        self,
        users: list[UserRef],
        filters: BugFilters | None = None,
    ) -> BugQueryResult:
        selected = filters or BugFilters()
        semaphore = asyncio.Semaphore(5)

        async def query(user: UserRef) -> tuple[UserRef, BugQueryResult | ZentaoError]:
            async with semaphore:
                try:
                    return user, await self.query_user_bugs(user, selected)
                except ZentaoError as exc:
                    return user, exc

        responses = await asyncio.gather(*(query(user) for user in users))
        bugs_by_id: dict[int, BugRecord] = {}
        failures: list[dict[str, str]] = []
        truncated = False
        for user, response in responses:
            if isinstance(response, ZentaoError):
                failures.append(
                    {
                        "account": user.account,
                        "code": response.code.value,
                        "message": response.message,
                    }
                )
                continue
            truncated = truncated or response.truncated
            bugs_by_id.update({bug.id: bug for bug in response.bugs})

        limit = selected.max_results or self._settings.query.max_results
        bugs = apply_filters(list(bugs_by_id.values()), selected)
        if len(bugs) > limit:
            bugs = bugs[:limit]
            truncated = True
        return BugQueryResult(
            bugs=bugs,
            summary=summarize_bugs(bugs),
            truncated=truncated,
            partial_failures=failures,
        )

    async def search_bugs(self, filters: BugFilters | None = None) -> BugQueryResult:
        selected = filters or BugFilters()
        limit = selected.max_results or self._settings.query.max_results
        paths = await self._scope_paths(selected)
        bugs_by_id: dict[int, BugRecord] = {}
        truncated = False

        for path in paths:
            remaining = limit - len(bugs_by_id)
            if remaining <= 0:
                truncated = True
                break
            page_bugs, page_truncated = await self._read_scope(path, selected, remaining)
            bugs_by_id.update({bug.id: bug for bug in page_bugs})
            truncated = truncated or page_truncated
            if len(bugs_by_id) >= limit:
                if path != paths[-1]:
                    truncated = True
                break

        bugs = apply_filters(list(bugs_by_id.values()), selected)[:limit]
        return BugQueryResult(
            bugs=bugs,
            summary=summarize_bugs(bugs),
            truncated=truncated,
        )

    async def _scope_paths(self, filters: BugFilters) -> list[str]:
        if filters.product_id:
            return [f"/products/{filters.product_id}/bugs"]
        if filters.project_id:
            return [f"/projects/{filters.project_id}/bugs"]
        if filters.execution_id:
            return [f"/executions/{filters.execution_id}/bugs"]
        return [f"/products/{product_id}/bugs" for product_id in await self._product_ids()]

    async def _product_ids(self) -> list[int]:
        page = 1
        product_ids: list[int] = []
        while True:
            payload = await self._client.request_json(
                "GET",
                "/products",
                params={
                    "page": page,
                    "recPerPage": self._settings.query.page_size,
                },
            )
            raw_products = _extract_list(payload, "products")
            for raw in raw_products:
                product_id = _id(raw.get("id"))
                if product_id is not None and product_id not in product_ids:
                    product_ids.append(product_id)
            total_pages = _page_total(payload)
            if (total_pages is not None and page >= total_pages) or (
                total_pages is None and len(raw_products) < self._settings.query.page_size
            ):
                break
            page += 1
        return product_ids

    async def _read_scope(
        self,
        path: str,
        filters: BugFilters,
        limit: int,
    ) -> tuple[list[BugRecord], bool]:
        page = 1
        bugs: list[BugRecord] = []
        seen: set[int] = set()
        while True:
            payload = await self._client.request_json(
                "GET",
                path,
                params={
                    "browseType": "unresolved" if filters.status == "unresolved" else "all",
                    "pageID": page,
                    "recPerPage": self._settings.query.page_size,
                },
            )
            raw_bugs = _extract_list(payload, "bugs")
            page_bugs = apply_filters(
                [parse_bug(raw) for raw in raw_bugs if raw.get("id")],
                filters,
            )
            for bug in page_bugs:
                if bug.id in seen:
                    continue
                if len(bugs) >= limit:
                    return bugs, True
                seen.add(bug.id)
                bugs.append(bug)

            total_pages = _page_total(payload)
            if len(bugs) >= limit:
                has_more = len(page_bugs) > len(bugs) or total_pages is None or page < total_pages
                return bugs, has_more
            if (total_pages is not None and page >= total_pages) or (
                total_pages is None and len(raw_bugs) < self._settings.query.page_size
            ):
                return bugs, False
            page += 1


def parse_bug(raw: Mapping[str, Any]) -> BugRecord:
    return BugRecord(
        id=int(str(raw["id"])),
        title=str(raw.get("title") or ""),
        status=str(raw.get("status") or ""),
        severity=raw.get("severity"),
        priority=raw.get("pri", raw.get("priority")),
        assigned_to=_account(raw.get("assignedTo", raw.get("assigned_to"))),
        opened_by=_account(raw.get("openedBy", raw.get("opened_by"))),
        product_id=_id(raw.get("product", raw.get("productID"))),
        project_id=_id(raw.get("project", raw.get("projectID"))),
        execution_id=_id(raw.get("execution", raw.get("executionID"))),
        bug_type=str(raw.get("type") or raw.get("bugType") or ""),
        opened_at=_datetime(raw.get("openedDate", raw.get("openedAt"))),
        edited_at=_datetime(raw.get("lastEditedDate", raw.get("editedAt"))),
        opened_build_ids=_build_ids(raw.get("openedBuild", raw.get("openedBuilds"))),
        steps=str(raw.get("steps") or ""),
        raw=dict(raw),
    )


def _extract_list(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    raw: Any = payload.get(key)
    if raw is None:
        raw = payload.get("data")
        if isinstance(raw, Mapping):
            raw = raw.get(key)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _page_total(payload: Mapping[str, Any]) -> int | None:
    pager = payload.get("pager")
    value = pager.get("pageTotal") if isinstance(pager, Mapping) else payload.get("pageTotal")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _account(value: object) -> str:
    if isinstance(value, Mapping):
        value = value.get("account") or value.get("id") or value.get("name")
    return str(value or "").strip()


def _id(value: object) -> int | None:
    if isinstance(value, Mapping):
        value = value.get("id")
    if value is None or value == "":
        return None
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed and parsed > 0 else None


def _datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _build_ids(value: object) -> list[str]:
    if value is None or value == "":
        return []
    items = value if isinstance(value, list) else [value]
    result: list[str] = []
    for item in items:
        if isinstance(item, Mapping):
            item = item.get("id") or item.get("name")
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result
