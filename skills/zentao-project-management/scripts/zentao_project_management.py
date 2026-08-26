#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED = REPO_ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.records import assignee, deadline_state, dedupe_records, is_open, priority, severity, status, title  # noqa: E402
from zentao.runtime import get_client, store_temp_json  # noqa: E402


WORKLOAD_RESOURCES = frozenset({"bug", "task", "story", "requirement", "test-task"})
OPEN_COUNT_RESOURCES = frozenset({"bug", "task", "story", "requirement", "test-task"})


def build_workload(resources: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = defaultdict(lambda: {"open_items": 0, "by_resource": {}})
    for resource, rows in resources.items():
        if resource not in WORKLOAD_RESOURCES:
            continue
        unique, _ = dedupe_records(rows)
        for row in unique:
            owner = assignee(row)
            if not owner or not is_open(resource, row):
                continue
            counts[owner]["open_items"] += 1
            per = counts[owner]["by_resource"]
            per[resource] = per.get(resource, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def build_health_report(scope: str, scope_id: int, resources: dict[str, list[dict[str, Any]]], *, today: str | date | None = None,
                        partial_failures: list[dict[str, object]] | None = None) -> dict[str, Any]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    for resource, rows in resources.items():
        normalized[resource], _ = dedupe_records(rows)
    signals: list[dict[str, Any]] = []
    severity_1 = [row for row in normalized.get("bug", []) if is_open("bug", row) and severity(row) == "1"]
    if severity_1:
        signals.append({"code": "severity_1_bug", "count": len(severity_1), "items": [{"id": row.get("id"), "title": title(row)} for row in severity_1]})
    priority_1 = [row for row in normalized.get("bug", []) if is_open("bug", row) and priority(row) == "1"]
    if priority_1:
        signals.append({"code": "priority_1_bug", "count": len(priority_1), "items": [{"id": row.get("id"), "title": title(row)} for row in priority_1]})
    overdue = [row for row in normalized.get("task", []) if deadline_state(row, resource="task", today=today) == "overdue"]
    if overdue:
        signals.append({"code": "overdue_task", "count": len(overdue), "items": [{"id": row.get("id"), "title": title(row)} for row in overdue]})
    unassigned = []
    for resource in ("bug", "task", "story", "requirement"):
        for row in normalized.get(resource, []):
            if is_open(resource, row) and not assignee(row):
                unassigned.append({"resource": resource, "id": row.get("id"), "title": title(row)})
    if unassigned:
        signals.append({"code": "unassigned_work", "count": len(unassigned), "items": unassigned})
    failures = list(partial_failures or [])
    if failures:
        signals.append({"code": "partial_data", "count": len(failures)})
    risk_codes = {item["code"] for item in signals}
    has_data = any(rows for rows in normalized.values())
    if failures and not has_data:
        overall = "unknown"
    else:
        overall = "risk" if risk_codes & {"severity_1_bug", "priority_1_bug", "overdue_task"} else "attention" if signals else "clear"
    resource_summary: dict[str, dict[str, Any]] = {}
    for resource, rows in normalized.items():
        item: dict[str, Any] = {"total": len(rows), "by_status": _status_counts(rows)}
        if resource in OPEN_COUNT_RESOURCES:
            item["open"] = sum(1 for row in rows if is_open(resource, row))
        resource_summary[resource] = item
    return {
        "scope": {"type": scope, "id": scope_id},
        "status": overall,
        "resources": resource_summary,
        "risk_signals": signals,
        "workload": build_workload(normalized),
        "complete": not failures,
        "partial_failures": failures,
    }


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = status(row)
        if value:
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _collect(client, scope: str, scope_id: int) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, object]]]:
    resources: dict[str, list[dict[str, Any]]] = {name: [] for name in ("bug", "task", "story", "test-case", "test-task", "build")}
    failures: list[dict[str, object]] = []
    if scope == "execution":
        browse_by_resource = {"bug": "all", "task": "all", "story": "all-story", "test-case": "all", "test-task": "all", "build": "all"}
        for resource in resources:
            try:
                listed = client.list_all(resource, scope="execution", scope_id=scope_id, browse=browse_by_resource[resource])
                resources[resource].extend(listed.items)
                failures.extend({"resource": resource, **item} for item in listed.partial_failures)
            except Exception as exc:
                failures.append({"resource": resource, "message": str(exc)})
        return resources, failures
    if scope != "project":
        raise ValueError("scope 只支持 project / execution")
    browse_by_resource = {"bug": "all", "story": "all-story", "test-case": "all", "test-task": "all", "build": "all"}
    for resource in ("bug", "story", "test-case", "test-task", "build"):
        try:
            listed = client.list_all(resource, scope="project", scope_id=scope_id, browse=browse_by_resource[resource])
            resources[resource].extend(listed.items)
            failures.extend({"resource": resource, **item} for item in listed.partial_failures)
        except Exception as exc:
            failures.append({"resource": resource, "message": str(exc)})
    try:
        executions = client.list_all("execution", scope="project", scope_id=scope_id, browse="all").items
    except Exception as exc:
        executions = []
        failures.append({"resource": "execution", "message": str(exc)})
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
    parser = argparse.ArgumentParser(description="ZenTao project/execution management analysis")
    parser.add_argument("action", choices=("overview", "health", "risks", "workload"))
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--project", type=int)
    scope.add_argument("--execution", type=int)
    parser.add_argument("--today")
    parser.add_argument("--cache-data", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    scope_name = "project" if args.project is not None else "execution"
    scope_id = args.project if args.project is not None else args.execution
    try:
        client = get_client()
        resources, failures = _collect(client, scope_name, scope_id)
        report = build_health_report(scope_name, scope_id, resources, today=args.today, partial_failures=failures)
        if args.action == "workload":
            payload: object = {"scope": report["scope"], "workload": report["workload"], "complete": report["complete"], "partial_failures": failures}
        elif args.action == "risks":
            payload = {"scope": report["scope"], "status": report["status"], "risk_signals": report["risk_signals"], "complete": report["complete"], "partial_failures": failures}
        elif args.action == "overview":
            payload = {"scope": report["scope"], "resources": report["resources"], "complete": report["complete"], "partial_failures": failures}
        else:
            payload = report
        if args.cache_data and isinstance(payload, dict):
            payload["temp_data"] = store_temp_json("project-management", {"scope": report["scope"], "resources": resources})
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":") if args.json else None, indent=None if args.json else 2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": {"code": "PROJECT_MANAGEMENT_ERROR", "message": str(exc), "details": {}}}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
