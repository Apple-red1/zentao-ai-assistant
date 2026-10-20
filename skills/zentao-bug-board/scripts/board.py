from __future__ import annotations

import html
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
SHARED = ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.records import dedupe_records  # noqa: E402
from workdays import next_workday  # noqa: E402


TZ = ZoneInfo("Asia/Shanghai")
CUTOFF = time(16, 0)
QUEUE_ORDER = ("overdue", "today", "next_workday", "after_1600", "awaiting_test", "uncertain")
QUEUE_LABELS = {
    "overdue": "历史未完成",
    "today": "今天下班前必须解决",
    "next_workday": "下一个中国法定工作日 12:00 前解决",
    "after_1600": "16:00 后新增",
    "awaiting_test": "已解决待测试验证",
    "uncertain": "待核定 / 无法归类",
}


def _value(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and value != "":
            return value
    return None


def _priority(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 4 else None
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized.startswith("P"):
            normalized = normalized[1:]
        if len(normalized) == 1 and normalized in "01234":
            return int(normalized)
    return None


def _opened_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        value = value.strip()
        if len(value) <= 10 or value.startswith("0000-00-00"):
            return None  # A date alone cannot establish the 16:00 boundary.
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return parsed.replace(tzinfo=TZ) if parsed.tzinfo is None else parsed.astimezone(TZ)


def _account(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("account")
    if not isinstance(value, str):
        return None
    account = value.strip()
    return account if account and account.casefold() != "closed" else None


def _valid_bug_id(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 0 < value < 10**19
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return len(value) <= 19 and bool(value.lstrip("0"))
    return False


def _sort_key(row: dict[str, Any]) -> tuple[int, str, int, str]:
    raw_id = row.get("id")
    id_string = str(raw_id)
    numeric = id_string.isascii() and id_string.isdigit()
    normalized_id = id_string.lstrip("0") or "0" if numeric else id_string
    return (row["priority_number"] if row["priority_number"] is not None else 99,
            row.get("opened_at") or "9999", 0 if numeric else 1,
            f"{len(normalized_id):020d}:{normalized_id}" if numeric else normalized_id)


def build_board(project_id: int, project_name: str | None, rows: Iterable[dict[str, Any]],
                now: datetime, *, partial_failures: Iterable[dict[str, Any]] = (),
                scope: str = "project") -> dict[str, Any]:
    """Classify one captured list snapshot; never writes to ZenTao."""
    if scope not in {"project", "product"}:
        raise ValueError("Bug 评审表仅支持 Project 或 Product 范围")
    if now.tzinfo is None:
        raise ValueError("now must contain a timezone")
    now = now.astimezone(TZ)
    raw_rows = list(rows)
    unique, duplicates = dedupe_records(raw_rows)
    queues: dict[str, list[dict[str, Any]]] = {name: [] for name in QUEUE_ORDER}
    failures = list(partial_failures)
    warnings: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    for source in raw_rows:
        source_id = source.get("id")
        if source_id is None:
            continue
        key = str(source_id)
        if key in seen and seen[key] != source:
            warnings.append({"code": "DUPLICATE_CONFLICT", "bug_id": source_id})
        else:
            seen[key] = source

    for source in unique:
        current_status = str(_value(source, "status", "stage") or "").strip().lower()
        if current_status == "closed":
            continue
        pri = _priority(_value(source, "pri", "priority"))
        opened = _opened_at(_value(source, "openedDate", "opened_date", "createdDate", "created_date"))
        item: dict[str, Any] = {
            "id": source.get("id"), "title": str(_value(source, "title", "name") or "未知"),
            "priority": f"P{pri}" if pri is not None else None, "priority_number": pri,
            "opened_at": opened.strftime("%Y-%m-%d %H:%M:%S") if opened else None,
            "due": None, "due_basis": None,
            "dev_owner": _account(_value(source, "assignedTo", "assigned_to", "assignedToAccount"))
                         if current_status == "active" else None,
            "resolved_by": _account(_value(source, "resolvedBy", "resolvedByAccount"))
                           if current_status == "resolved" else None,
            "test_owner": _account(_value(source, "assignedTo", "assigned_to", "assignedToAccount"))
                          if current_status == "resolved" else None,
            "status": current_status or None, "reason": None, "url": None,
        }
        reason = None
        if not _valid_bug_id(source.get("id")):
            reason = "Bug ID 缺失或无效"
        elif current_status not in {"active", "resolved"}:
            reason = "状态缺失或无法识别"
        elif pri is None:
            reason = "优先级缺失或无法映射到 P0～P4"
        elif opened is None:
            reason = "创建时刻缺失或精度不足，无法判断 16:00 边界"
        elif opened > now:
            reason = "创建时刻晚于本次查询时刻"
        if reason:
            item["reason"] = reason
            queues["uncertain"].append(item)
            warnings.append({"code": "BUG_UNCLASSIFIED", "bug_id": source.get("id"), "reason": reason})
            continue
        if current_status == "resolved":
            queues["awaiting_test"].append(item)
            continue
        assert opened is not None and pri is not None
        if opened.date() == now.date() and opened.time() >= CUTOFF:
            queues["after_1600"].append(item)
            continue
        intake_day = opened.date() + timedelta(days=1) if opened.time() >= CUTOFF else opened.date()
        if intake_day > now.date():
            item["reason"] = "尚未进入下一轮评审"
            queues["uncertain"].append(item)
            warnings.append({"code": "BUG_UNCLASSIFIED", "bug_id": source.get("id"), "reason": item["reason"]})
            continue
        if pri <= 2:
            item["due"] = f"{intake_day.isoformat()} 下班前"
            item["due_basis"] = "按当前优先级与创建时刻推算；历史优先级变更未核验"
            queues["overdue" if intake_day < now.date() else "today"].append(item)
            continue
        due_day = next_workday(intake_day)
        if due_day is None:
            item["reason"] = "所需年份的中国法定工作日日历尚未核验"
            queues["uncertain"].append(item)
            warnings.append({"code": "CALENDAR_UNKNOWN", "bug_id": source.get("id"), "reason": item["reason"]})
            continue
        item["due"] = f"{due_day.isoformat()} 12:00"
        item["due_basis"] = "按当前优先级与创建时刻推算；历史优先级变更未核验"
        deadline = datetime.combine(due_day, time(12), tzinfo=TZ)
        queues["overdue" if now >= deadline else "next_workday"].append(item)

    for items in queues.values():
        items.sort(key=_sort_key)
        for item in items:
            item.pop("priority_number")
    return {
        scope: {"id": project_id, "name": project_name},
        "as_of": now.isoformat(timespec="seconds"), "timezone": "Asia/Shanghai",
        "complete": not failures and not warnings,
        "partial_failures": failures, "data_warnings": warnings,
        "duplicates": duplicates,
        "counts": {key: len(items) for key, items in queues.items()}, "queues": queues,
    }


def resolve_target(client: Any, name: str) -> tuple[str, int]:
    """Resolve a unique visible Project/Product name, allowing a spoken 项目 suffix."""
    requested = name.strip()
    if not requested:
        raise ValueError("请提供 Project 或 Product 名称")
    candidates: list[tuple[str, int, str]] = []
    for scope in ("project", "product"):
        options = {"browse": "all"} if scope == "product" else {}
        listed = client.list_all(scope, preserve_partial=True, **options)
        if not listed.complete:
            raise ValueError("Project/Product 列表查询不完整，无法唯一确认名称")
        for row in listed.items:
            try:
                row_id = int(row.get("id"))
            except (TypeError, ValueError):
                continue
            if row_id > 0 and isinstance(row.get("name"), str):
                candidates.append((scope, row_id, row["name"].strip()))
    for candidate_name in (requested, requested[:-2].strip() if requested.endswith("项目") else ""):
        if not candidate_name:
            continue
        matches = {(scope, row_id) for scope, row_id, row_name in candidates if row_name == candidate_name}
        if len(matches) == 1:
            return next(iter(matches))
        if len(matches) > 1:
            raise ValueError("Project/Product 名称重名，无法唯一确认；请提供明确的 --project 或 --product ID")
    raise ValueError("未找到该名称的可见 Project 或 Product；请核对名称或提供明确 ID")


def collect_board(client: Any, project_id: int, now: datetime, *, scope: str = "project") -> dict[str, Any]:
    if scope not in {"project", "product"}:
        raise ValueError("Bug 评审表仅支持 Project 或 Product 范围")
    label = scope.capitalize()
    if project_id <= 0:
        raise ValueError(f"{label} ID 必须为正整数")
    options = {"browse": "all"} if scope == "product" else {}
    listed_scope = client.list_all(scope, preserve_partial=True, **options)
    matches = [row for row in listed_scope.items if str(row.get("id")) == str(project_id)]
    names = {str(row.get("name") or "") for row in matches}
    if not matches or len(names) != 1:
        raise ValueError(f"{label} 不存在、不可见或列表不完整，无法唯一确认 {label} ID")
    listed_bugs = client.list_all("bug", scope=scope, scope_id=project_id,
                                  browse="all", preserve_partial=True)
    failures = list(listed_bugs.partial_failures)
    if not listed_scope.complete:
        failures.extend({"resource": scope, **failure} for failure in listed_scope.partial_failures)
        if not listed_scope.partial_failures:
            failures.append({"code": f"{scope.upper()}_LIST_INCOMPLETE", "resource": scope})
    if not listed_bugs.complete and not listed_bugs.partial_failures:
        failures.append({"code": "BUG_LIST_INCOMPLETE"})
    report = build_board(project_id, str(matches[0].get("name") or ""), listed_bugs.items, now,
                         partial_failures=failures, scope=scope)
    ids = sorted({int(item["id"]) for queue in report["queues"].values() for item in queue
                  if _valid_bug_id(item.get("id"))})
    if ids:
        try:
            links = client.bug_web_urls(ids)
            url_map = {int(item["id"]): item["url"] for item in links
                       if isinstance(item, dict) and isinstance(item.get("id"), int)
                       and isinstance(item.get("url"), str) and item["url"]}
        except Exception:
            url_map = {}
        for queue in report["queues"].values():
            for item in queue:
                bug_id = item.get("id")
                if _valid_bug_id(bug_id):
                    item["url"] = url_map.get(int(bug_id))
                    if item["url"] is None:
                        report["data_warnings"].append({"code": "BUG_URL_FAILED", "bug_id": bug_id})
                        report["complete"] = False
    return report


def _cell(value: Any) -> str:
    if value is None or value == "":
        return "未知"
    text = html.escape(str(value), quote=False).replace("\\", "\\\\")
    for char in ("|", "[", "]", "*", "_", "`", "#"):
        text = text.replace(char, "\\" + char)
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def render_board(report: Mapping[str, Any]) -> str:
    scope = "product" if "product" in report else "project"
    target = report[scope]
    lines = [f"# 16:00 Bug 评审表 · {_cell(target.get('name'))} ({scope.capitalize()} {target['id']})", "",
             f"查询时刻：{report['as_of']}（{report['timezone']}）", "",
             "数据状态：" + ("完整" if report["complete"] else "查询不完整或存在待核定数据"), "",
             "期限依据：按当前优先级和创建时刻推算；历史优先级变更未由本次列表核验。", ""]
    headers = ("Bug ID", "标题", "优先级", "提出时间", "完成要求", "研发负责人", "开发解决人", "测试负责人", "状态/说明")
    for key in QUEUE_ORDER:
        items = report["queues"][key]
        lines.extend([f"## {QUEUE_LABELS[key]}（{len(items)}）", ""])
        if not items:
            lines.extend(["无。", ""])
            continue
        lines.extend(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"])
        for item in items:
            bug_id = item.get("id")
            link = item.get("url")
            id_cell = f"[{_cell(bug_id)}]({link})" if link else _cell(bug_id) + "（链接待核定）"
            values = (item.get("title"), item.get("priority"), item.get("opened_at"),
                      item.get("due"), item.get("dev_owner"), item.get("resolved_by"),
                      item.get("test_owner"), item.get("reason") or item.get("status"))
            lines.append("| " + " | ".join((id_cell, *(_cell(value) for value in values))) + " |")
        lines.append("")
    if not report["complete"]:
        lines.extend(["## 数据完整性", "", "查询不完整；以上仅是已读取且可分类的记录，不能视作目标范围全部待办。", ""])
    for failure in report["partial_failures"]:
        lines.append(f"- 读取失败：{_cell(failure.get('code'))}，第 {_cell(failure.get('page'))} 页")
    for warning in report["data_warnings"]:
        lines.append(f"- 数据待核定：{_cell(warning.get('code'))}，Bug {_cell(warning.get('bug_id'))}")
    if report["partial_failures"] or report["data_warnings"]:
        lines.append("")
    return "\n".join(lines).rstrip()
