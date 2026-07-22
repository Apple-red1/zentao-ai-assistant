import pytest
from pydantic import ValidationError

from zentao_ai.zentao.models import (
    BugPage,
    BugSnapshot,
    Coverage,
    ItemFailure,
    ResolvedIdentity,
)


def test_bug_page_serializes_partial_item_failures_and_resolved_identity() -> None:
    page = BugPage(
        items=(
            BugSnapshot(
                id="42",
                status="active",
                version="2026-07-21T08:00:00Z",
                snapshotVersion="2026-07-21T08:00:00Z",
                snapshotStable=True,
            ),
        ),
        coverage=Coverage(
            page=1,
            pageSize=20,
            total=2,
            pages=1,
            returned=1,
            failed=1,
            complete=False,
        ),
        itemFailures=(
            ItemFailure(
                bugId="43",
                code="MISSING_STABLE_VERSION",
                field="version",
                message="missing stable version",
            ),
        ),
        resolvedIdentity=ResolvedIdentity(
            requestedIdentity="Alice Example",
            resolvedAccount="alice",
            resolvedDisplayName="Alice Example",
            matchType="display_name",
        ),
    )

    assert page.coverage.complete is False
    assert page.coverage.returned == 1
    assert page.coverage.failed == 1
    serialized = page.model_dump(by_alias=True, exclude={"items"})
    assert serialized["itemFailures"] == (
        {
            "bugId": "43",
            "code": "MISSING_STABLE_VERSION",
            "field": "version",
            "message": "missing stable version",
        },
    )
    assert serialized["resolvedIdentity"] == {
        "requestedIdentity": "Alice Example",
        "resolvedAccount": "alice",
        "resolvedDisplayName": "Alice Example",
        "matchType": "display_name",
    }


def test_coverage_rejects_failures_claimed_as_complete() -> None:
    with pytest.raises(ValidationError, match="failed results cannot be complete"):
        Coverage(returned=1, failed=1, complete=True)


def test_bug_page_rejects_item_failures_claimed_as_complete() -> None:
    with pytest.raises(ValidationError, match="item failures require incomplete coverage"):
        BugPage(
            items=(),
            coverage=Coverage(returned=0, failed=0, complete=True),
            itemFailures=(
                ItemFailure(
                    bugId="43",
                    code="MISSING_STABLE_VERSION",
                    field="version",
                    message="missing stable version",
                ),
            ),
        )


def test_bug_snapshot_accepts_explicit_unstable_versionless_row() -> None:
    bug = BugSnapshot.model_validate(
        {
            "id": 3422,
            "title": "SEO Rule-twitter",
            "priority": "P3",
            "status": "active",
            "assignee": "zhouhaiyin",
            "version": None,
            "snapshotVersion": None,
            "snapshotStable": False,
        }
    )

    assert bug.snapshot_version is None
    assert bug.snapshot_stable is False
    assert bug.priority == "P3"


def test_stable_snapshot_requires_matching_nonempty_version() -> None:
    with pytest.raises(ValueError, match="stable snapshot requires version"):
        BugSnapshot(
            id=1,
            status="active",
            version=None,
            snapshotVersion=None,
            snapshotStable=True,
        )


def test_stable_snapshot_rejects_mismatched_nonempty_versions() -> None:
    with pytest.raises(ValueError, match="stable snapshot requires matching version"):
        BugSnapshot(
            id=1,
            status="active",
            version="v1",
            snapshotVersion="v2",
            snapshotStable=True,
        )


def test_coverage_accepts_unstable_snapshot_count_alias() -> None:
    coverage = Coverage(unstableSnapshots=2)

    assert coverage.unstable_snapshots == 2
    assert coverage.model_dump(by_alias=True)["unstableSnapshots"] == 2
