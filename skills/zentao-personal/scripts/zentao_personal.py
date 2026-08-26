#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED = REPO_ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.records import assignee, deadline_state, dedupe_records, is_open, priority, severity, title  # noqa: E402
from zentao.identity import AmbiguousMatchError, MatchNotFoundError, resolve_user  # noqa: E402
from zentao.runtime import get_client, store_temp_json  # noqa: E402


def _risk_item(resource: str, row: dict[str, Any], *, today: str | date | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "resource": resource,
        "id": row.get("id"),
        "title": title(row),
        "status": row.get("status"),
    }
    pri = priority(row)
    sev = severity(row)
    if pri:
        item["priority"] = pri
    if sev:
        item["severity"] = sev
    if resource == "task":
        item["deadline_state"] = deadline_state(row, resource="task", today=today)
        if row.get("deadline") not in (None, ""):
            item["deadline"] = row.get("deadline")
    return item


def build_personal_overview(account: str, resources: dict[str, list[dict[str, Any]]], *, today: str | date | None = None,
                            partial_failures: list[dict[str, object]] | None = None) -> dict[str, Any]:
    selected: dict[str, list[dict[str, Any]]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for resource, rows in resources.items():
        mine, _ = dedupe_records(row for row in rows if assignee(row) == account)
        selected[resource] = mine
        summaries[resource] = {
            "total": len(mine),
            "open": sum(1 for row in mine if is_open(resource, row)),
        }
    severity_1_bugs = [_risk_item("bug", row, today=today) for row in selected.get("bug", []) if is_open("bug", row) and severity(row) == "1"]
    priority_1_bugs = [_risk_item("bug", row, today=today) for row in selected.get("bug", []) if is_open("bug", row) and priority(row) == "1"]
    overdue_tasks = [_risk_item("task", row, today=today) for row in selected.get("task", []) if deadline_state(row, resource="task", today=today) == "overdue"]
    upcoming_tasks = [_risk_item("task", row, today=today) for row in selected.get("task", []) if deadline_state(row, resource="task", today=today) == "upcoming"]
    high_priority = [
        {"resource": resource, "id": row.get("id"), "title": title(row)}
        for resource, rows in selected.items() for row in rows
        if is_open(resource, row) and priority(row) == "1"
    ]
    return {
        "account": account,
        "resources": summaries,
        "total_items": sum(item["total"] for item in summaries.values()),
        "open_items": sum(item["open"] for item in summaries.values()),
        "risks": {
            "severity_1_bugs": severity_1_bugs,
            "priority_1_bugs": priority_1_bugs,
            "overdue_tasks": overdue_tasks,
            "upcoming_tasks": upcoming_tasks,
            "high_priority": high_priority,
        },
        "partial_failures": list(partial_failures or []),
        "complete": not partial_failures,
    }


def build_worklist(account: str, resources: dict[str, list[dict[str, Any]]], *, today: str | date | None = None) -> list[dict[str, Any]]:
    items = []
    for resource, rows in resources.items():
        for row in rows:
            if assignee(row) != account or not is_open(resource, row):
                continue
            deadline = deadline_state(row, resource="task", today=today) if resource == "task" else None
            rank = 0 if deadline == "overdue" else 1 if (resource == "bug" and severity(row) == "1") else 2 if priority(row) == "1" else 3
            items.append({"resource": resource, "id": row.get("id"), "title": title(row), "status": row.get("status"), "deadline_state": deadline, "priority": priority(row), "rank": rank})
    return sorted(items, key=lambda item: (item["rank"], str(item["resource"]), str(item["id"])))


def _collect(client) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, object]]]:
    resources: dict[str, list[dict[str, Any]]] = {name: [] for name in ("bug", "task", "story", "requirement", "ticket", "feedback")}
    failures: list[dict[str, object]] = []
    try:
        products = client.list_all("product", browse="all").items
    except Exception as exc:
        products = []
        failures.append({"resource": "product", "message": str(exc)})
    try:
        executions = client.list_all("execution", browse="all").items
    except Exception as exc:
        executions = []
        failures.append({"resource": "execution", "message": str(exc)})
    product_browse = {"bug": "all", "story": "all-story", "requirement": "all-story", "ticket": "all", "feedback": "all"}
    for product in products:
        try:
            product_id = int(product["id"])
        except (KeyError, TypeError, ValueError):
            continue
        for resource in ("bug", "story", "requirement", "ticket", "feedback"):
            try:
                listed = client.list_all(resource, scope="product", scope_id=product_id, browse=product_browse[resource])
                resources[resource].extend(listed.items)
                failures.extend({"resource": resource, "scope": f"product:{product_id}", **item} for item in listed.partial_failures)
            except Exception as exc:
                failures.append({"resource": resource, "scope": f"product:{product_id}", "message": str(exc)})
    for execution in executions:
        try:
            execution_id = int(execution["id"])
        except (KeyError, TypeError, ValueError):
            continue
        try:
            listed = client.list_all("task", scope="execution", scope_id=execution_id, browse="all")
            resources["task"].extend(listed.items)
            failures.extend({"resource": "task", "scope": f"execution:{execution_id}", **item} for item in listed.partial_failures)
        except Exception as exc:
            failures.append({"resource": "task", "scope": f"execution:{execution_id}", "message": str(exc)})
    return resources, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ZenTao personal work assistant")
    parser.add_argument("action", choices=("overview", "worklist", "brief"))
    parser.add_argument("--user")
    parser.add_argument("--today")
    parser.add_argument("--cache-data", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        client = get_client()
        account = client.account
        if args.user:
            users = []
            for browse in ("inside", "outside"):
                users.extend(client.list_all("user", browse=browse).items)
            users, _ = dedupe_records(users)
            target = resolve_user(users, args.user)
            resolved_account = target.get("account") or target.get("id")
            if resolved_account in (None, ""):
                raise ValueError(f"用户缺少可用 account/id: {args.user}")
            account = str(resolved_account)
        if not account:
            raise ValueError("无法确定当前 ZenTao account")
        resources, failures = _collect(client)
        overview = build_personal_overview(account, resources, today=args.today, partial_failures=failures)
        if args.action == "worklist":
            payload: object = {"account": account, "items": build_worklist(account, resources, today=args.today), "complete": overview["complete"], "partial_failures": failures}
        elif args.action == "brief":
            payload = {"account": account, "summary": overview["resources"], "risks": overview["risks"], "open_items": overview["open_items"], "complete": overview["complete"], "partial_failures": failures}
        else:
            payload = overview
        if args.cache_data and isinstance(payload, dict):
            payload["temp_data"] = store_temp_json("personal", {"account": account, "resources": resources})
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":") if args.json else None, indent=None if args.json else 2))
        return 0
    except AmbiguousMatchError as exc:
        candidates = list(exc.candidates)
        message = f"用户姓名存在歧义: {', '.join(candidates)}"
        print(json.dumps({"error": {"code": "USER_AMBIGUOUS", "message": message, "details": {"user": exc.value, "candidates": candidates}}}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1
    except MatchNotFoundError as exc:
        message = f"未找到用户: {exc.value}"
        print(json.dumps({"error": {"code": "PERSONAL_ERROR", "message": message, "details": {}}}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1
    except Exception as exc:
        print(json.dumps({"error": {"code": "PERSONAL_ERROR", "message": str(exc), "details": {}}}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
