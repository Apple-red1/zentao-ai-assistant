from __future__ import annotations

from zentao_ai.zentao.models import BugPage


def _cell(value: object) -> str:
    text = "unknown" if value is None or str(value).strip() == "" else str(value)
    return " ".join(text.splitlines()).replace("|", r"\|")


def render_bug_table(page: BugPage) -> str:
    lines = [
        "| Bug号 | 标题 | 优先级 | 状态 | 负责人 | 快照稳定性 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for bug in page.items:
        stable = "稳定" if bug.snapshot_stable else "不稳定"
        cells = (bug.id, bug.title, bug.priority, bug.status, bug.assignee, stable)
        lines.append("| " + " | ".join(_cell(value) for value in cells) + " |")
    if not page.items:
        lines.append("| - | 无 | - | - | - | - |")
    return "\n".join(lines)
