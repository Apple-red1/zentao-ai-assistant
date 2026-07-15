#!/usr/bin/env python3
"""Render deterministic Zentao personal and team daily Markdown reports."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


class ReportError(ValueError):
    pass


def require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReportError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReportError(f"{field} must be an array")
    return value


def text(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ReportError(f"{field} must be nonempty")
    return result


def optional_text(value: Any) -> str | None:
    result = str(value or "").strip()
    return result or None


def integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReportError(f"{field} must be a nonnegative integer")
    return value


def join_cn(values: Any, field: str) -> str:
    items = [text(item, field) for item in require_list(values, field)]
    return "、".join(items)


def comment_result(comment: dict[str, Any]) -> str:
    status = text(comment.get("status"), "comment.status")
    comment_id = optional_text(comment.get("commentId")) or "None"
    return f"{status} / {comment_id}"


def routing_line(routing_value: Any) -> str:
    routing = require_mapping(routing_value, "routing")
    selected = optional_text(routing.get("selectedRepository"))
    layer = optional_text(routing.get("layer")) or "unknown"
    keywords = join_cn(routing.get("matchedKeywords", []), "routing.matchedKeywords")
    if selected:
        return f"路由：{selected} / {layer}；关键词：{keywords}。"
    candidates = join_cn(routing.get("candidates", []), "routing.candidates")
    return (
        f"路由：selectedRepository=null，layer={layer}；"
        f"候选为 {candidates}；关键词：{keywords}。"
    )


def validate_personal_partition(information: list[Any], walkthrough: list[Any]) -> None:
    seen: set[str] = set()
    for item in [*information, *walkthrough]:
        bug = require_mapping(item, "bug")
        bug_id = text(bug.get("id"), "bug.id")
        if bug_id in seen:
            raise ReportError(f"duplicate Bug across personal report groups: {bug_id}")
        seen.add(bug_id)


def render_information_bug(value: Any) -> list[str]:
    bug = require_mapping(value, "informationBug")
    comment = require_mapping(bug.get("comment"), "comment")
    lines = [
        f"{text(bug.get('id'), 'bug.id')}｜当前状态：{text(bug.get('status'), 'bug.status')}｜判断：{text(bug.get('decision'), 'bug.decision')}",
        routing_line(bug.get("routing")),
        f"是否修改代码：{'是' if bug.get('patchChanged') is True else '否'}",
        f"快照版本：{text(bug.get('snapshotVersion'), 'bug.snapshotVersion')}",
        f"原因：{text(bug.get('reason'), 'bug.reason')}",
        f"AI评论：{comment_result(comment)}",
    ]
    comment_text = optional_text(comment.get("text"))
    status = text(comment.get("status"), "comment.status")
    if comment_text and status in {"CREATED", "ALREADY_EXISTS"}:
        lines.append(f"备注：AI已在禅道上添加备注文字：{comment_text}")
    elif comment_text:
        lines.append(f"备注：拟添加备注（写入失败）：{comment_text}")
    else:
        lines.append("备注：无")
    return lines


def render_walkthrough_bug(value: Any) -> list[str]:
    bug = require_mapping(value, "walkthroughBug")
    tests = require_mapping(bug.get("tests"), "tests")
    comment = require_mapping(bug.get("comment"), "comment")
    tests_summary = text(tests.get("summary"), "tests.summary")
    if tests.get("completed") is not True and "未声称修复完成" not in tests_summary:
        tests_summary = f"{tests_summary.rstrip('。')}；未声称修复完成。"
    return [
        f"{text(bug.get('id'), 'bug.id')}｜当前状态：{text(bug.get('status'), 'bug.status')}｜判断：{text(bug.get('decision'), 'bug.decision')}",
        routing_line(bug.get("routing")),
        f"是否修改代码：{'是' if bug.get('patchChanged') is True else '否'}",
        f"快照版本：{text(bug.get('snapshotVersion'), 'bug.snapshotVersion')}",
        f"门禁：{text(bug.get('gateSummary'), 'bug.gateSummary')}",
        f"根因证据：{text(bug.get('rootCauseEvidence'), 'bug.rootCauseEvidence')}",
        f"测试：{tests_summary}",
        f"禅道备注：{comment_result(comment)}",
    ]


def render_personal(payload: dict[str, Any]) -> str:
    run = require_mapping(payload.get("run"), "run")
    coverage = require_mapping(payload.get("coverage"), "coverage")
    information = require_list(payload.get("informationBugs", []), "informationBugs")
    walkthrough = require_list(payload.get("walkthroughBugs", []), "walkthroughBugs")
    validate_personal_partition(information, walkthrough)

    lines = [
        "# 个人 Bug 日报",
        "",
        f"业务日期：{text(run.get('businessDate'), 'run.businessDate')}（Asia/Shanghai）",
        f"快照截止：{text(run.get('snapshotCutoff'), 'run.snapshotCutoff')}",
        f"运行类型：{text(run.get('runType'), 'run.runType')}",
        f"覆盖范围：{join_cn(coverage.get('scopes'), 'coverage.scopes')}",
        f"完整性：{text(coverage.get('completeness'), 'coverage.completeness')}",
        "",
        "## 等待补充信息 Bug",
        "",
    ]
    if information:
        for index, bug in enumerate(information):
            if index:
                lines.append("")
            lines.extend(render_information_bug(bug))
    else:
        lines.append("无")

    lines.extend(["", "## 人工需走查 Bug", ""])
    if walkthrough:
        for index, bug in enumerate(walkthrough):
            if index:
                lines.append("")
            lines.extend(render_walkthrough_bug(bug))
    else:
        lines.append("无")
    return "\n".join(lines).rstrip() + "\n"


def render_team(payload: dict[str, Any]) -> str:
    run = require_mapping(payload.get("run"), "run")
    coverage = require_mapping(payload.get("coverage"), "coverage")
    members = require_list(coverage.get("members"), "coverage.members")
    candidates = require_list(payload.get("candidateBugs", []), "candidateBugs")

    rows: list[tuple[str, int, int, int]] = []
    for value in members:
        member = require_mapping(value, "member")
        rows.append((
            text(member.get("name"), "member.name"),
            integer(member.get("unclosedCandidates"), "member.unclosedCandidates"),
            integer(member.get("p1"), "member.p1"),
            integer(member.get("stale7Days"), "member.stale7Days"),
        ))
    totals = tuple(sum(row[index] for row in rows) for index in range(1, 4))

    lines = [
        "# 团队 Bug 汇总",
        "",
        f"业务日期：{text(run.get('businessDate'), 'run.businessDate')}（Asia/Shanghai）",
        f"快照时间：{text(run.get('snapshotCutoff'), 'run.snapshotCutoff')}",
        f"覆盖成员：{len(rows)} 人",
        f"执行模式：{text(run.get('executionMode'), 'run.executionMode')}",
        f"写操作：{text(run.get('writeOperations'), 'run.writeOperations')}",
        "",
        "| 成员 | 未关闭候选 | P1 | 7天以上无活动 |",
        "| --- | ---: | ---: | ---: |",
    ]
    lines.extend(f"| {name} | {unclosed} | {p1} | {stale} |" for name, unclosed, p1, stale in rows)
    lines.extend([
        f"| 合计 | {totals[0]} | {totals[1]} | {totals[2]} |",
        "",
        "候选 Bug：",
    ])
    if candidates:
        for value in candidates:
            bug = require_mapping(value, "candidateBug")
            lines.append(
                f"{text(bug.get('id'), 'bug.id')}：{text(bug.get('title'), 'bug.title')}，"
                f"负责人{text(bug.get('assignee'), 'bug.assignee')}，"
                f"{text(bug.get('status'), 'bug.status')}，{text(bug.get('priority'), 'bug.priority')}"
            )
    else:
        lines.append("无")
    lines.extend([
        "",
        f"完整性：{text(coverage.get('completeness'), 'coverage.completeness')}",
        text(payload.get("leaseSummary"), "leaseSummary"),
    ])
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("personal", "team"))
    return parser


def main() -> int:
    # Windows uses the active console code page for redirected standard streams.
    # The automation contract is UTF-8 JSON in and UTF-8 Markdown out.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    try:
        payload = require_mapping(json.load(sys.stdin), "payload")
        output = render_personal(payload) if args.mode == "personal" else render_team(payload)
    except (json.JSONDecodeError, ReportError) as error:
        print(str(error), file=sys.stderr)
        return 2
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
