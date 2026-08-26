#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED = REPO_ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.records import assignee, deadline_state, dedupe_records, first_value, group_count, priority, scalar_identity, severity, status  # noqa: E402
from zentao.runtime import get_client, store_temp_json  # noqa: E402

SUPPORTED = ("bug", "task", "story", "requirement", "test-case", "test-task", "ticket", "feedback")

DEFAULT_BROWSE = {
    "bug": "all",
    "task": "all",
    "story": "all-story",
    "requirement": "all-story",
    "test-case": "all",
    "test-task": "all",
    "ticket": "all",
    "feedback": "all",
}

SCOPES = {
    "bug": {"product", "project", "execution"},
    "task": {"execution"},
    "story": {"product", "project", "execution"},
    "requirement": {"product"},
    "test-case": {"product", "project", "execution"},
    "test-task": {"product", "project", "execution"},
    "ticket": {"product"},
    "feedback": {"product"},
}


def summarize_records(resource: str, records: list[dict[str, Any]], *, complete: bool = True,
                      partial_failures: list[dict[str, object]] | None = None, today: str | date | None = None) -> dict[str, Any]:
    unique, duplicates = dedupe_records(records)
    result: dict[str, Any] = {
        "resource": resource,
        "total": len(unique),
        "by_status": group_count(unique, status),
        "by_assignee": group_count(unique, assignee),
        "complete": bool(complete),
        "partial_failures": list(partial_failures or []),
        "duplicates_removed": duplicates,
    }
    by_priority = group_count(unique, priority)
    if by_priority:
        result["by_priority"] = by_priority
    if resource == "bug":
        result["by_severity"] = group_count(unique, severity)
        result["by_type"] = group_count(unique, lambda row: scalar_identity(first_value(row, "type")))
    if resource in {"story", "requirement"}:
        result["by_stage"] = group_count(unique, lambda row: scalar_identity(first_value(row, "stage")))
    if resource == "task":
        counts = Counter(deadline_state(row, resource="task", today=today) for row in unique)
        counts.pop(None, None)
        result["deadline"] = {key: counts.get(key, 0) for key in ("overdue", "upcoming", "future", "completed_past_deadline", "completed")}
    return result


def compare_summaries(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"comparisons": items}


def _scope_from_args(args: argparse.Namespace) -> tuple[str, int]:
    values = [(name, getattr(args, name)) for name in ("product", "project", "execution") if getattr(args, name) is not None]
    if len(values) != 1:
        raise ValueError("必须且只能指定一个 --product / --project / --execution")
    return values[0]


def _load_summary(client, resource: str, scope: str, scope_id: int, *, browse: str | None, per_page: int, today: str | None, cache_data: bool) -> dict[str, Any]:
    if scope not in SCOPES[resource]:
        raise ValueError(f"{resource} 不支持 {scope} scope")
    effective_browse = browse if browse is not None else DEFAULT_BROWSE[resource]
    listed = client.list_all(resource, scope=scope, scope_id=scope_id, browse=effective_browse, per_page=per_page)
    summary = summarize_records(resource, listed.items, complete=listed.complete, partial_failures=listed.partial_failures, today=today)
    summary["scope"] = {"type": scope, "id": scope_id}
    summary["pages"] = listed.pages
    if cache_data:
        summary["temp_data"] = store_temp_json("statistics", {"resource": resource, "scope": summary["scope"], "items": listed.items})
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZenTao deterministic statistics")
    sub = parser.add_subparsers(dest="action", required=True)
    summary = sub.add_parser("summary")
    summary.add_argument("resource", choices=SUPPORTED)
    for name in ("product", "project", "execution"):
        summary.add_argument(f"--{name}", type=int)
    summary.add_argument("--browse")
    summary.add_argument("--per-page", type=int, default=1000)
    summary.add_argument("--today")
    summary.add_argument("--cache-data", action="store_true")
    summary.add_argument("--json", action="store_true")

    compare = sub.add_parser("compare")
    compare.add_argument("resource", choices=SUPPORTED)
    compare.add_argument("--scope", action="append", required=True, help="scope type and id, e.g. product:1")
    compare.add_argument("--browse")
    compare.add_argument("--per-page", type=int, default=1000)
    compare.add_argument("--today")
    compare.add_argument("--cache-data", action="store_true")
    compare.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = get_client()
        if args.action == "summary":
            scope, scope_id = _scope_from_args(args)
            payload = _load_summary(client, args.resource, scope, scope_id, browse=args.browse, per_page=args.per_page, today=args.today, cache_data=args.cache_data)
        else:
            values = []
            compare_scope_type: str | None = None
            for raw in args.scope:
                scope, sep, ident = raw.partition(":")
                if not sep or not ident.isdigit():
                    raise ValueError("--scope 必须使用 type:id")
                if compare_scope_type is None:
                    compare_scope_type = scope
                elif scope != compare_scope_type:
                    raise ValueError("compare 只允许比较同一种 scope 类型")
                summary = _load_summary(client, args.resource, scope, int(ident), browse=args.browse, per_page=args.per_page, today=args.today, cache_data=args.cache_data)
                values.append({"scope": summary.pop("scope"), "summary": summary})
            payload = compare_summaries(values)
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":") if args.json else None, indent=None if args.json else 2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": {"code": "STATISTICS_ERROR", "message": str(exc), "details": {}}}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
