#!/usr/bin/env python3
"""Deterministic, read-only Bug selection and evidence snapshot helpers."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED = REPO_ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.identity import AmbiguousMatchError, MatchNotFoundError, resolve_named_entity, resolve_user  # noqa: E402
from zentao.records import dedupe_records, scalar_identity  # noqa: E402
from zentao.runtime import get_client  # noqa: E402
COLLECTIONS = {"bug": "bugs", "product": "products", "project": "projects", "execution": "executions", "user": "users"}
SCOPES = ("product", "project", "execution")
TIME_ALIASES = {
    "created": ("openedDate", "createdDate", "createdAt", "created_at"),
    "updated": ("lastEditedDate", "editedDate", "updatedDate", "updatedAt", "updated_at"),
}
FIELD_ALIASES = {
    "status": ("status", "stage"),
    "priority": ("pri", "priority"),
    "severity": ("severity",),
    "assignee": ("assignedTo", "assigned_to", "assignee", "assignedToAccount", "owner"),
}
CRITICAL_FIELDS = ("id", "status", "assignee", "title", "description", "severity", "priority", "product", "project", "execution", "module", "affected_build", "creator_account", "created", "updated")
CRITICAL_ALIASES = {"id": ("id",), "status": FIELD_ALIASES["status"], "assignee": FIELD_ALIASES["assignee"], "title": ("title", "name"), "description": ("steps", "description", "desc"), "severity": ("severity",), "priority": ("pri", "priority"), "product": ("product", "productID", "product_id"), "project": ("project", "projectID", "project_id"), "execution": ("execution", "executionID", "execution_id"), "module": ("module", "moduleID", "module_id"), "affected_build": ("openedBuild", "affectedBuild", "affected_build", "resolvedBuild"), "created": TIME_ALIASES["created"], "updated": TIME_ALIASES["updated"]}
CREATOR_ACCOUNT_KEYS = ("openedByAccount", "creatorAccount", "createdByAccount", "creator_account", "opened_by_account", "created_by_account")
CREATOR_OBJECT_KEYS = ("openedBy", "opened_by", "creator", "createdBy", "openedByUser", "creatorUser")
def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("必须是正整数") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return parsed
def _validate_args(args: argparse.Namespace) -> None:
    if sum(getattr(args, name, None) is not None for name in ("product", "project", "execution")) > 1:
        raise ValueError("必须且只能指定一个 --product / --project / --execution")
    if args.bug_id and any(getattr(args, name, None) not in (None, [], "") for name in (
        "user", "product", "project", "execution", "module", "status", "priority", "severity",
        "created_after", "created_before", "updated_after", "updated_before",
    )):
        raise ValueError("--bug-id 不能与查询条件组合")
    if args.per_page < 1 or args.per_page > 1000:
        raise ValueError("per-page 必须在 1..1000")
def _record_id(row: dict[str, Any]) -> str | None:
    value = row.get("id")
    return None if value in (None, "") else str(value)
def _scope_label(resource: str, scope: str | None, scope_id: int | None) -> str:
    return f"{resource}:{scope_id}" if scope else resource
def _failure(code: str, *, resource: str, scope: str | None, page: int | None = None, message: str | None = None, **extra: object) -> dict[str, object]:
    item: dict[str, object] = {"code": code, "resource": resource, "scope": _scope_label(resource, scope, extra.pop("scope_id", None))}
    if page is not None:
        item["page"] = page
    if message:
        item["message"] = str(message)
    item.update(extra)
    return item
def _total(payload: dict[str, Any]) -> int | None:
    pager = payload.get("pager")
    if not isinstance(pager, dict):
        return None
    value = pager.get("total")
    if isinstance(value, int) and not isinstance(value, bool):
        return value if value >= 0 else None
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
def paginate_pages(client: Any, resource: str, *, scope: str | None = None, scope_id: int | None = None,
                   browse: str | None = None, per_page: int = 1000, max_pages: int = 10000) -> dict[str, Any]:
    """Read one public-facade collection while retaining partial successful pages."""
    if resource not in COLLECTIONS or per_page < 1 or per_page > 1000:
        raise ValueError("资源或 per-page 参数无效")
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, object]] = []
    seen: set[str] = set()
    total: int | None = None
    page = 1
    while page <= max_pages:
        try:
            payload = client.list_page(resource, scope=scope, scope_id=scope_id, page=page, per_page=per_page, browse=browse)
        except Exception as exc:
            failures.append(_failure("PAGE_READ_FAILED", resource=resource, scope=scope, scope_id=scope_id, page=page, message=str(exc)))
            return {"items": rows, "complete": False, "pages": page - 1, "partial_failures": failures}
        if not isinstance(payload, dict) or not isinstance(payload.get(COLLECTIONS[resource]), list) or any(not isinstance(row, dict) for row in payload[COLLECTIONS[resource]]):
            failures.append(_failure("PAGE_RESPONSE_INVALID", resource=resource, scope=scope, scope_id=scope_id, page=page))
            return {"items": rows, "complete": False, "pages": page, "partial_failures": failures}
        page_rows = payload[COLLECTIONS[resource]]
        total = _total(payload) if _total(payload) is not None else total
        page_ids = [ident for row in page_rows if (ident := _record_id(row)) is not None]
        only_ids = bool(page_rows) and len(page_ids) == len(page_rows)
        new_ids = set(page_ids) - seen if only_ids else set()
        if only_ids:
            if page > 1 and not new_ids:
                failures.append(_failure("PAGINATION_STALLED", resource=resource, scope=scope, scope_id=scope_id, page=page, expected_total=total, received=len(seen)))
                return {"items": rows, "complete": False, "pages": page, "partial_failures": failures}
            seen.update(page_ids)
        rows.extend(page_rows)
        received = len(seen) if only_ids else len(rows)
        if total is not None and received >= total:
            return {"items": rows, "complete": True, "pages": page, "partial_failures": failures}
        if not page_rows:
            if total in (None, 0):
                return {"items": rows, "complete": True, "pages": page, "partial_failures": failures}
            failures.append(_failure("PAGINATION_STALLED", resource=resource, scope=scope, scope_id=scope_id, page=page, expected_total=total, received=received))
            return {"items": rows, "complete": False, "pages": page, "partial_failures": failures}
        if total is None and len(page_rows) < per_page:
            return {"items": rows, "complete": True, "pages": page, "partial_failures": failures}
        page += 1
    failures.append(_failure("MAX_PAGES_REACHED", resource=resource, scope=scope, scope_id=scope_id, max_pages=max_pages))
    return {"items": rows, "complete": False, "pages": max_pages, "partial_failures": failures}
def _read_all(client: Any, resource: str, *, scope: str | None = None, scope_id: int | None = None,
              browse: str | None = None, per_page: int = 1000) -> dict[str, Any]:
    result = paginate_pages(client, resource, scope=scope, scope_id=scope_id, browse=browse, per_page=per_page)
    unique, duplicates = dedupe_records(result["items"])
    result["items"] = unique
    result["duplicates_removed"] = duplicates
    return result


def _entity_scope(client: Any, resource: str, value: str, *, per_page: int) -> tuple[int, dict[str, Any]]:
    if value.isdigit() and int(value) > 0:
        return int(value), {"pages": 0, "complete": True, "partial_failures": []}
    listed = _read_all(client, resource, browse="all", per_page=per_page)
    entity = resolve_named_entity(listed["items"], value, kind=resource)
    try:
        ident = int(entity["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MatchNotFoundError(resource, value) from exc
    return ident, listed


def _users(client: Any, *, per_page: int) -> dict[str, Any]:
    results = [_read_all(client, "user", browse=browse, per_page=per_page) for browse in ("inside", "outside")]
    rows, duplicates = dedupe_records(row for result in results for row in result["items"])
    return {
        "items": rows,
        "pages": sum(result["pages"] for result in results),
        "complete": all(result["complete"] for result in results),
        "partial_failures": [failure for result in results for failure in result["partial_failures"]],
        "duplicates_removed": duplicates,
    }


def _value(row: dict[str, Any], aliases: tuple[str, ...]) -> tuple[bool, Any]:
    found = False
    for key in aliases:
        if key in row:
            found = True
            if row[key] not in (None, ""):
                return True, row[key]
    if found:
        return False, None
    return False, None


def _module_id(row: dict[str, Any]) -> tuple[bool, str | None]:
    """Read a module identifier without ever treating a module name as an ID."""
    for key in ("moduleID", "module_id", "module"):
        if key not in row:
            continue
        value = row[key]
        if isinstance(value, dict):
            value = value.get("id")
        if isinstance(value, bool) or value in (None, ""):
            continue
        text = str(value)
        if text.isdigit() and int(text) > 0:
            return True, str(int(text))
    return False, None


def _parse_time(value: Any) -> date | datetime:
    text = str(value).strip()
    if not text:
        raise ValueError("时间过滤器不能为空")
    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"非法 ISO 时间: {value}") from exc


def _record_time(value: Any) -> date | datetime | None:
    try:
        return _parse_time(value)
    except ValueError:
        return None


def _time_matches(value: date | datetime, after: date | datetime | None, before: date | datetime | None) -> bool | None:
    try:
        if isinstance(after, date) and not isinstance(after, datetime) and isinstance(value, datetime):
            value = value.date()
        if isinstance(before, date) and not isinstance(before, datetime) and isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date) and not isinstance(value, datetime) and (isinstance(after, datetime) or isinstance(before, datetime)):
            return None
        return (after is None or value >= after) and (before is None or value <= before)
    except TypeError:
        return None


def _unsupported(name: str, rows: list[dict[str, Any]], missing: list[str]) -> dict[str, object]:
    ids = sorted(set(missing), key=lambda value: (0, int(value)) if value.isdigit() else (1, value))
    return {"filter": name, "missing_ids": ids, "count": len(ids)}


def filter_records(rows: list[dict[str, Any]], *, user: str | None = None, module: int | None = None,
                   statuses: list[str] | None = None, priorities: list[str] | None = None,
                   severities: list[str] | None = None, created_after: str | None = None,
                   created_before: str | None = None, updated_after: str | None = None,
                   updated_before: str | None = None) -> tuple[list[dict[str, Any]], list[dict[str, object]]]:
    filters: list[tuple[str, Callable[[dict[str, Any]], tuple[bool, bool]]]] = []

    def scalar_filter(name: str, aliases: tuple[str, ...], expected: list[str]) -> None:
        wanted = {str(value) for value in expected}
        filters.append((name, lambda row: (lambda present, value: (present, present and scalar_identity(value) in wanted))(*_value(row, aliases))))

    if user is not None:
        scalar_filter("user", FIELD_ALIASES["assignee"], [user])
    if module is not None:
        wanted_module = str(module)
        filters.append(("module", lambda row: (lambda present, value: (present, present and value == wanted_module))(*_module_id(row))))
    if statuses:
        scalar_filter("status", FIELD_ALIASES["status"], statuses)
    if priorities:
        scalar_filter("priority", FIELD_ALIASES["priority"], priorities)
    if severities:
        scalar_filter("severity", FIELD_ALIASES["severity"], severities)

    for name, after_text, before_text in (("created", created_after, created_before), ("updated", updated_after, updated_before)):
        if after_text is None and before_text is None:
            continue
        after = _parse_time(after_text) if after_text is not None else None
        before = _parse_time(before_text) if before_text is not None else None
        filters.append((name, lambda row, aliases=TIME_ALIASES[name], after=after, before=before: (lambda present, raw: (present, False if not present else (_time_matches(parsed, after, before) if (parsed := _record_time(raw)) is not None else None)))(*_value(row, aliases))))

    missing: dict[str, list[str]] = {name: [] for name, _ in filters}
    matched: list[dict[str, Any]] = []
    for row in rows:
        included = True
        for name, predicate in filters:
            present, result = predicate(row)
            if not present or result is None:
                ident = _record_id(row)
                if ident is not None:
                    missing[name].append(ident)
                included = False
            elif not result:
                included = False
        if included:
            matched.append(row)
    return matched, [_unsupported(name, rows, values) for name, values in missing.items() if values]


def extract_creator_account(bug: dict[str, Any]) -> str | None:
    for key in CREATOR_ACCOUNT_KEYS:
        value = bug.get(key)
        if isinstance(value, dict):
            value = value.get("account")
        if value not in (None, "") and not isinstance(value, (list, dict)):
            return str(value)
    for key in CREATOR_OBJECT_KEYS:
        value = bug.get(key)
        if isinstance(value, dict) and value.get("account") not in (None, ""):
            return str(value["account"])
    return None


def _critical_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return scalar_identity(value)
    return value


def normalize_critical(bug: dict[str, Any]) -> dict[str, Any]:
    critical: dict[str, Any] = {}
    for field in CRITICAL_FIELDS:
        if field == "creator_account":
            critical[field] = extract_creator_account(bug)
            continue
        present, value = _value(bug, CRITICAL_ALIASES[field])
        critical[field] = _critical_value(value) if present else None
    return critical


def build_snapshot(bug_id: int, bug: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(bug, dict):
        raise ValueError("Bug 详情不是对象")
    critical = normalize_critical(bug)
    return {"bug_id": bug_id, "bug": bug, "critical": critical, "unavailable_fields": [field for field in CRITICAL_FIELDS if critical[field] is None]}


def _valid_baseline(bug_id: int, baseline: Any) -> dict[str, Any]:
    if not isinstance(baseline, dict) or type(baseline.get("bug_id")) is not int or baseline.get("bug_id") != bug_id or not isinstance(baseline.get("bug"), dict) or not isinstance(baseline.get("critical"), dict):
        raise ValueError("baseline 不是同一 Bug 的 snapshot")
    critical = baseline["critical"]
    unavailable = baseline.get("unavailable_fields")
    expected_unavailable = [field for field in CRITICAL_FIELDS if critical.get(field) is None]
    if set(critical) != set(CRITICAL_FIELDS) or not isinstance(unavailable, list) or unavailable != expected_unavailable or any(not isinstance(field, str) for field in unavailable):
        raise ValueError("baseline critical 字段不完整")
    return baseline


def compare_snapshots(bug_id: int, baseline: dict[str, Any], bug: dict[str, Any]) -> dict[str, Any]:
    baseline = _valid_baseline(bug_id, baseline)
    current = build_snapshot(bug_id, bug)
    changes = [{"field": field, "before": baseline["critical"].get(field), "after": current["critical"].get(field)} for field in CRITICAL_FIELDS if baseline["critical"].get(field) != current["critical"].get(field)]
    unavailable = [field for field in CRITICAL_FIELDS if field in set(baseline["unavailable_fields"]) | set(current["unavailable_fields"])]
    return {
        "bug_id": bug_id,
        "changed": bool(changes) or bool(unavailable),
        "comparison_blocked": bool(unavailable),
        "block_reason": "CRITICAL_FIELD_UNAVAILABLE" if unavailable else None,
        "changes": changes,
        "baseline": baseline["critical"],
        "current": current["critical"],
        "unavailable_fields": unavailable,
    }

def _read_view(client: Any, bug_id: int) -> dict[str, Any]:
    value = client.view("bug", bug_id)
    if not isinstance(value, dict):
        raise ValueError("Bug 详情不是对象")
    value = value.get("bug", value)
    if not isinstance(value, dict):
        raise ValueError("Bug 详情不是对象")
    return value
def _read_baseline(path: str, bug_id: int) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as handle:
            return _valid_baseline(bug_id, json.load(handle))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 baseline snapshot: {path}") from exc


def _query_rows(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    pages = 0
    complete = True
    failures: list[dict[str, object]] = []
    duplicates = 0
    scopes = [name for name in SCOPES if getattr(args, name) is not None]
    if len(scopes) > 1:
        raise ValueError("必须且只能指定一个 --product / --project / --execution")
    scope_name = scopes[0] if scopes else None
    scope_info: dict[str, Any] = {"pages": 0, "complete": True, "partial_failures": []}
    scope_id: int | None = None
    if scope_name:
        scope_id, scope_info = _entity_scope(client, scope_name, getattr(args, scope_name), per_page=args.per_page)
        pages += scope_info["pages"]
        complete = complete and scope_info["complete"]
        failures.extend(scope_info["partial_failures"])

    user_account: str | None = None
    if args.user is not None:
        users = _users(client, per_page=args.per_page)
        pages += users["pages"]
        complete = complete and users["complete"]
        failures.extend(users["partial_failures"])
        target = resolve_user(users["items"], args.user)
        account = target.get("account")
        if account in (None, ""):
            raise MatchNotFoundError("user", args.user)
        user_account = str(account)

    all_rows: list[dict[str, Any]] = []
    if scope_name:
        listed = _read_all(client, "bug", scope=scope_name, scope_id=scope_id, browse=args.browse or "all", per_page=args.per_page)
        all_rows.extend(listed["items"])
        pages += listed["pages"]
        complete = complete and listed["complete"]
        failures.extend({**failure, "scope": f"{scope_name}:{scope_id}"} for failure in listed["partial_failures"])
        duplicates += listed["duplicates_removed"]
    else:
        products = _read_all(client, "product", browse="all", per_page=args.per_page)
        pages += products["pages"]
        complete = complete and products["complete"]
        failures.extend(products["partial_failures"])
        duplicates += products["duplicates_removed"]
        for product in products["items"]:
            product_id = _record_id(product)
            if product_id is None or not product_id.isdigit() or int(product_id) <= 0:
                complete = False
                failures.append({"code": "INVALID_SCOPE_RECORD", "resource": "product", "scope": "product", "message": "产品记录缺少正整数 id"})
                continue
            listed = _read_all(client, "bug", scope="product", scope_id=int(product_id), browse=args.browse or "all", per_page=args.per_page)
            all_rows.extend(listed["items"])
            pages += listed["pages"]
            complete = complete and listed["complete"]
            failures.extend({**failure, "scope": f"product:{product_id}"} for failure in listed["partial_failures"])
            duplicates += listed["duplicates_removed"]
    unique, bug_duplicates = dedupe_records(all_rows)
    duplicates += bug_duplicates
    filtered, unsupported = filter_records(unique, user=user_account, module=args.module, statuses=args.status,
                                           priorities=args.priority, severities=args.severity,
                                           created_after=args.created_after, created_before=args.created_before,
                                           updated_after=args.updated_after, updated_before=args.updated_before)
    complete = complete and not unsupported
    return {"items": filtered, "complete": complete, "pages": pages, "duplicates_removed": duplicates,
            "partial_failures": failures, "unsupported_filters": unsupported}


def select_bugs(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    _validate_args(args)
    if args.bug_id:
        ids: list[int] = []
        seen: set[int] = set()
        for value in args.bug_id:
            if value not in seen:
                ids.append(value)
                seen.add(value)
        return {"mode": "ids", "current_bug_id": ids[0] if ids else None, "pending_queue": ids[1:],
                "items": [{"id": value} for value in ids], "complete": True, "pages": 0,
                "duplicates_removed": len(args.bug_id) - len(ids), "partial_failures": [],
                "unsupported_filters": [], "ambiguous_matches": []}
    result = _query_rows(client, args)
    items = result["items"]
    items, _ = dedupe_records(items)
    items.sort(key=lambda row: (0, int(row["id"])) if str(row.get("id", "")).isdigit() else (1, str(row.get("id", ""))))
    ids = [row.get("id") for row in items if row.get("id") not in (None, "")]
    return {"mode": "query", "current_bug_id": ids[0] if ids else None, "pending_queue": ids[1:],
            "items": items, "complete": result["complete"], "pages": result["pages"],
            "duplicates_removed": result["duplicates_removed"], "partial_failures": result["partial_failures"],
            "unsupported_filters": result["unsupported_filters"], "ambiguous_matches": []}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZenTao evidence-driven Bug resolver read operations")
    sub = parser.add_subparsers(dest="action", required=True)
    select = sub.add_parser("select", help="选择当前 Bug 并保留待处理队列")
    select.add_argument("--bug-id", action="append", type=_positive_int)
    select.add_argument("--user")
    for name in SCOPES:
        select.add_argument(f"--{name}")
    select.add_argument("--module", type=_positive_int)
    select.add_argument("--status", action="append", default=[])
    select.add_argument("--priority", action="append", default=[])
    select.add_argument("--severity", action="append", default=[])
    select.add_argument("--created-after")
    select.add_argument("--created-before")
    select.add_argument("--updated-after")
    select.add_argument("--updated-before")
    select.add_argument("--browse")
    select.add_argument("--per-page", type=_positive_int, default=1000)
    select.add_argument("--json", action="store_true")
    snapshot = sub.add_parser("snapshot", help="读取 Bug 快照")
    snapshot.add_argument("--bug-id", type=_positive_int, required=True)
    snapshot.add_argument("--json", action="store_true")
    compare = sub.add_parser("compare", help="比较写前 Bug 快照")
    compare.add_argument("--bug-id", type=_positive_int, required=True)
    compare.add_argument("--baseline-file", required=True)
    compare.add_argument("--json", action="store_true")
    return parser


def _error(code: str, message: str, details: dict[str, Any] | None = None) -> int:
    print(json.dumps({"error": {"code": code, "message": message, "details": details or {}}}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = get_client()
        if args.action == "select":
            _validate_args(args)
            payload = select_bugs(client, args)
        elif args.action == "snapshot":
            payload = build_snapshot(args.bug_id, _read_view(client, args.bug_id))
        elif args.action == "compare":
            payload = compare_snapshots(args.bug_id, _read_baseline(args.baseline_file, args.bug_id), _read_view(client, args.bug_id))
        else:
            return _error("RESOLVER_USAGE", "不支持的操作")
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":") if args.json else None, indent=None if args.json else 2))
        return 0
    except AmbiguousMatchError as exc:
        return _error("AMBIGUOUS_MATCH", str(exc), {"kind": exc.kind, "value": exc.value, "candidates": exc.candidates})
    except MatchNotFoundError as exc:
        return _error("MATCH_NOT_FOUND", str(exc), {"kind": exc.kind, "value": exc.value})
    except ValueError as exc:
        return _error("RESOLVER_USAGE", str(exc))
    except Exception as exc:
        return _error("RESOLVER_ERROR", str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
