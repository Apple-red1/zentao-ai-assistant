from __future__ import annotations

from datetime import UTC, datetime

from zentao_ai.bugs import apply_filters, parse_bug
from zentao_ai.models import BugFilters, BugRecord


def sample_bugs() -> list[BugRecord]:
    return [
        BugRecord(
            id=101,
            title="登录失败",
            status="active",
            severity=1,
            priority=1,
            assigned_to="zhangsan",
            opened_by="lisi",
            product_id=3,
            opened_at=datetime(2026, 7, 1, tzinfo=UTC),
        ),
        BugRecord(
            id=102,
            title="报表错位",
            status="resolved",
            severity=2,
            priority=2,
            assigned_to="zhangsan",
            opened_by="wangwu",
            product_id=3,
            opened_at=datetime(2026, 7, 2, tzinfo=UTC),
        ),
        BugRecord(
            id=103,
            title="登录页面文案",
            status="active",
            severity=3,
            priority=3,
            assigned_to="lisi",
            opened_by="zhangsan",
            product_id=4,
            opened_at=datetime(2026, 7, 3, tzinfo=UTC),
        ),
    ]


def test_filters_can_be_combined() -> None:
    filters = BugFilters(
        status="unresolved",
        assigned_to=["zhangsan"],
        severity=[1],
        keyword="登录",
    )

    assert [bug.id for bug in apply_filters(sample_bugs(), filters)] == [101]


def test_all_status_keeps_resolved_and_closed_bugs() -> None:
    assert len(apply_filters(sample_bugs(), BugFilters(status="all"))) == 3


def test_date_ranges_are_inclusive() -> None:
    filters = BugFilters(
        status="all",
        opened_after=datetime(2026, 7, 2, tzinfo=UTC),
        opened_before=datetime(2026, 7, 3, tzinfo=UTC),
    )

    assert [bug.id for bug in apply_filters(sample_bugs(), filters)] == [102, 103]


def test_bug_parser_accepts_opened_build_objects() -> None:
    bug = parse_bug(
        {
            "id": "9",
            "title": "Build mapping",
            "openedBuild": [{"id": 12, "name": "v1"}, "trunk"],
        }
    )

    assert bug.opened_build_ids == ["12", "trunk"]
