from __future__ import annotations

from zentao_ai.bugs import summarize_bugs
from zentao_ai.models import BugRecord


def test_summary_counts_and_sorts_dimensions() -> None:
    summary = summarize_bugs(
        [
            BugRecord(
                id=2,
                title="B",
                status="active",
                severity=2,
                priority=1,
                assigned_to="lisi",
            ),
            BugRecord(
                id=1,
                title="A",
                status="active",
                severity=1,
                priority=2,
                assigned_to="zhangsan",
            ),
        ]
    )

    assert summary.total == 2
    assert list(summary.by_assignee) == ["lisi", "zhangsan"]
    assert summary.by_status == {"active": 2}
    assert summary.by_priority == {"1": 1, "2": 1}
    assert summary.by_severity == {"1": 1, "2": 1}

