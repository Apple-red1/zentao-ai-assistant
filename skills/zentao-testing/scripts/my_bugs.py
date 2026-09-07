"""Deterministic current-project/global personal Bug aggregation."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED = REPO_ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.records import assignee, priority, severity, status, title  # noqa: E402
from project_config import TestingConfigError, context_view  # noqa: E402


KNOWN_STATUSES = frozenset({"active", "resolved", "closed"})


def _id(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit() and int(value) > 0:
        return int(value)
    return None


def _failure(code: str, *, page: int | None = None, scope: str | None = None, **details: object) -> dict[str, object]:
    result: dict[str, object] = {"code": code}
    if page is not None:
        result["page"] = page
    if scope is not None:
        result["scope"] = scope
    result.update(details)
    return result


def _list_bugs(client: object, *, scope: str, scope_id: int, per_page: int) -> tuple[list[dict[str, Any]], list[dict[str, object]]]:
    try:
        listed = client.list_all("bug", scope=scope, scope_id=scope_id, browse="all", per_page=per_page,
                                preserve_partial=True)
    except Exception:
        return [], [_failure("BUG_SCOPE_READ_FAILED", scope=f"{scope}:{scope_id}")]
    failures = [_failure(str(item.get("code", "PAGE_READ_FAILED")), scope=f"{scope}:{scope_id}", **{
        key: value for key, value in item.items() if key != "code"
    }) for item in getattr(listed, "partial_failures", [])]
    return list(getattr(listed, "items", []) or []), failures


def _scope_rows(client: object, *, all_projects: bool, project_id: int | None, product_id: int,
                per_page: int) -> tuple[list[dict[str, Any]], list[dict[str, object]]]:
    if not all_projects:
        if project_id is None:
            return _list_bugs(client, scope="product", scope_id=product_id, per_page=per_page)
        return _list_bugs(client, scope="project", scope_id=project_id, per_page=per_page)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, object]] = []
    # The public scopes overlap; reconciliation below is deliberately by ID.
    for resource in ("product", "project", "execution"):
        try:
            entities = client.list_all(resource, browse="all", per_page=per_page, preserve_partial=True)
        except Exception:
            failures.append(_failure("SCOPE_DIRECTORY_READ_FAILED", scope=resource))
            continue
        failures.extend(_failure(str(item.get("code", "PAGE_READ_FAILED")), scope=resource, **{
            key: value for key, value in item.items() if key != "code"
        }) for item in getattr(entities, "partial_failures", []))
        for entity in getattr(entities, "items", []) or []:
            entity_id = _id(entity.get("id")) if isinstance(entity, dict) else None
            if entity_id is None:
                failures.append(_failure("SCOPE_ID_INVALID", scope=resource))
                continue
            page_rows, page_failures = _list_bugs(client, scope=resource, scope_id=entity_id, per_page=per_page)
            rows.extend(page_rows)
            failures.extend(page_failures)
    return rows, failures


def _normalize_rows(rows: list[dict[str, Any]], account: str, *, module_id: int | None) -> tuple[list[dict[str, Any]], int, list[dict[str, object]]]:
    candidates: dict[int, list[dict[str, Any]]] = {}
    failures: list[dict[str, object]] = []
    for row in rows:
        ident = _id(row.get("id"))
        if ident is None:
            failures.append(_failure("BUG_ID_INVALID"))
            continue
        current_status = status(row).strip().casefold()
        if current_status not in KNOWN_STATUSES:
            failures.append(_failure("BUG_STATUS_INVALID", bug_id=ident))
            continue
        current_assignee = assignee(row)
        if not current_assignee or current_assignee != account or current_status == "closed":
            continue
        if module_id is not None:
            actual_module = _id(row.get("module") or row.get("moduleID") or row.get("module_id"))
            if actual_module != module_id:
                continue
        candidates.setdefault(ident, []).append(row)
    duplicates_removed = sum(max(0, len(values) - 1) for values in candidates.values())
    normalized: list[dict[str, Any]] = []
    for ident, values in candidates.items():
        first = values[0]
        def fingerprint(row: dict[str, Any]) -> tuple[object, ...]:
            return status(row), assignee(row), title(row), priority(row), severity(row)
        if any(fingerprint(row) != fingerprint(first) for row in values[1:]):
            failures.append(_failure("BUG_SNAPSHOT_CONFLICT", bug_id=ident))
            continue
        normalized.append({"id": ident, "title": title(first), "status": status(first),
                           "priority": priority(first) or None, "severity": severity(first) or None,
                           "assignee": assignee(first)})
    return normalized, duplicates_removed, failures


def _sort_key(item: dict[str, Any]) -> tuple[int, int, int, int]:
    phase = {"active": 0, "resolved": 1}.get(str(item["status"]).casefold(), 2)
    def number(value: object) -> int:
        return int(value) if isinstance(value, str) and value.isascii() and value.isdigit() else 10**9
    return phase, number(item.get("priority")), number(item.get("severity")), -int(item["id"])


def collect_my_bugs(client: object, *, all_projects: bool = False, module_id: int | None = None,
                    per_page: int = 1000, root: Path | None = None) -> dict[str, Any]:
    if not 1 <= per_page <= 1000:
        raise TestingConfigError("PER_PAGE_INVALID", "per-page 必须在 1..1000")
    context = context_view(client, root=root)
    project = context["project"]
    project_id = project.get("project_id")
    if project_id is not None:
        project_id = int(project_id)
    product_id = int(project["product_id"])
    failures = list(context.get("partial_failures", []))
    rows, scope_failures = _scope_rows(client, all_projects=all_projects, project_id=project_id,
                                       product_id=product_id, per_page=per_page)
    failures.extend(scope_failures)
    items, duplicates_removed, row_failures = _normalize_rows(rows, client.account, module_id=module_id)
    failures.extend(row_failures)
    items.sort(key=_sort_key)
    try:
        links = client.bug_web_urls([item["id"] for item in items])
    except Exception:
        links = []
        failures.append(_failure("BUG_WEB_URL_FAILED"))
    by_id = {item.get("id"): item.get("url") for item in links if isinstance(item, dict)}
    for item in items:
        item["web_url"] = by_id.get(item["id"])
        if not item["web_url"]:
            failures.append(_failure("BUG_WEB_URL_FAILED", bug_id=item["id"]))
    scope: dict[str, Any] = {"mode": "all_projects" if all_projects else
                             ("current_project" if project_id is not None else "current_product")}
    scope["project_alias"] = context["current"]["project_alias"]
    if not all_projects:
        scope["project_id" if project_id is not None else "product_id"] = project_id or product_id
    return {"scope": scope, "account": client.account, "items": items,
            "duplicates_removed": duplicates_removed, "complete": not failures,
            "partial_failures": failures}


__all__ = ["collect_my_bugs"]
