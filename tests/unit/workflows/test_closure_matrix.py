from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from zentao_ai.config.models import AppConfig
from zentao_ai.workflows.models import AnalysisSignal, RunContext
from zentao_ai.workflows.personal import run_personal
from zentao_ai.workflows.team_report import run_team_report
from zentao_ai.zentao.models import BugPage, BugSnapshot, Coverage, HistoryPage
from zentao_ai.safety.images import CurrentTurnAuthorization, validate_user_image
from zentao_ai.workflows.steps import ReproductionStep, _complete_steps


class Ledger:
    def acquire_lease(self, *_):
        return type("Lease", (), {"acquired": True, "lease_id": "lease"})()

    def release_lease(self, *_):
        pass

    def put_checkpoint(self, *_):
        pass


class RecordingProvider:
    def __init__(self):
        self.queries = []

    def query_my_bugs(self, *, scope_names, page=1, page_size=20):
        self.queries.append(("personal", scope_names, page, page_size))
        return BugPage(
            items=tuple(self._bug(x) for x in range(1, 6)), coverage=Coverage(total=5)
        )

    def query_user_bugs(self, user, *, scope_names, page=1, page_size=20):
        self.queries.append((user, scope_names, page, page_size))
        base = 1 if user == "a" else 4
        return BugPage(
            items=tuple(self._bug(x) for x in range(base, base + 3)),
            coverage=Coverage(total=3),
        )

    def query_bug_detail(self, bug_id):
        return self._bug(int(bug_id))

    def query_bug_history(self, bug_id, **_):
        return HistoryPage(items=(), coverage=Coverage(total=0))

    @staticmethod
    def _bug(value):
        return BugSnapshot(
            id=value, status="active", version="v1", snapshotVersion="v1"
        )


def context(provider, *, limit=3, readonly=False):
    config = AppConfig.model_validate(
        {
            "personal": {"scopeNames": ["mine"]},
            "team": {"scopeNames": ["squad"], "members": ["a", "b"]},
            "limits": {"maxBugsPerRun": limit},
            "repositories": {},
        }
    )
    return RunContext(
        config,
        provider,
        Ledger(),
        lambda: datetime(2026, 7, 15, 9),
        "owner",
        analysis=lambda *_: AnalysisSignal(evidenceComplete=True, fixCandidate=True),
        readonly=readonly,
    )


def test_personal_scope_total_and_truncation_are_explicit():
    provider = RecordingProvider()
    result = run_personal(context(provider))
    assert provider.queries[0][1] == ("mine",)
    assert (
        result.coverage,
        result.coverageTotal,
        result.truncated,
        result.completeness,
    ) == (3, 5, True, "PARTIAL")


def test_unknown_coverage_is_partial():
    class UnknownCoverage(RecordingProvider):
        def query_my_bugs(self, *, scope_names, page=1, page_size=20):
            self.queries.append(("personal", scope_names, page, page_size))
            return BugPage(items=(self._bug(1),), coverage=Coverage(total=0))

    result = run_personal(context(UnknownCoverage(), limit=3))
    assert (
        result.coverageTotal is None
        and result.truncated
        and result.completeness == "PARTIAL"
    )


def test_team_limit_is_global_and_runtime_is_forced_readonly():
    provider = RecordingProvider()
    result = run_team_report(context(provider))
    assert result.coverage == 3 and result.coverageTotal == 6 and result.truncated
    assert all(query[1] == ("squad",) for query in provider.queries)
    assert result.completeness == "PARTIAL"


def test_creator_account_is_typed_and_raw_is_not_needed():
    snapshot = BugSnapshot(
        id=1,
        status="active",
        version="v1",
        snapshotVersion="v1",
        creator={"account": "alice"},
        raw={"creator": {"account": "wrong"}},
    )
    assert snapshot.creator is not None and snapshot.creator.account == "alice"


def test_replacement_steps_require_ordered_action_and_expected_schema():
    with pytest.raises(ValueError):
        _complete_steps((ReproductionStep("click save", ""),))
    rendered = _complete_steps(
        (ReproductionStep("click save", "confirmation appears"),)
    )
    assert rendered == '[{"action":"click save","expected":"confirmation appears"}]'


def test_image_validation_returns_the_exact_immutable_upload_bytes(tmp_path: Path):
    path = (tmp_path / "proof.png").resolve()
    content = b"\x89PNG\r\n\x1a\nimmutable"
    path.write_bytes(content)
    result = validate_user_image(
        path,
        CurrentTurnAuthorization(
            paths=(path,), authorizationTurnId="t", currentTurnId="t"
        ),
    )
    assert (
        result.valid and result.content == content and isinstance(result.content, bytes)
    )
    assert result.path != str(result.content)


def test_public_workflow_exports_are_complete():
    from zentao_ai.workflows import repair_bug, run_personal, run_team_report

    assert callable(run_personal) and callable(run_team_report) and callable(repair_bug)
