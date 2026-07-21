from __future__ import annotations

from datetime import datetime
from typing import NoReturn

import pytest

from zentao_ai.config.models import AppConfig
from zentao_ai.state.models import LeaseResult, RunStatus
from zentao_ai.workflows.models import AnalysisSignal, RunContext
from zentao_ai.workflows.personal import run_personal
from zentao_ai.workflows.team_report import run_team_report
from zentao_ai.zentao.models import (
    BugPage,
    BugSnapshot,
    Coverage,
    HistoryPage,
    RoutingData,
)


def bug(value: int) -> BugSnapshot:
    return BugSnapshot(id=value, status="active", version="v1", snapshotVersion="v1")


class RecordingLedger:
    def __init__(self, *, acquired: bool = True) -> None:
        self.acquired = acquired
        self.acquisitions: list[tuple[object, ...]] = []
        self.releases: list[tuple[str, object]] = []
        self.checkpoints: list[tuple[object, str, object]] = []

    def acquire_lease(self, *args: object) -> LeaseResult:
        self.acquisitions.append(args)
        return LeaseResult(self.acquired, "lease", "owner", "later")

    def release_lease(self, lease_id: str, status: object) -> None:
        self.releases.append((lease_id, status))

    def put_checkpoint(self, business: object, kind: str, payload: object) -> None:
        self.checkpoints.append((business, kind, payload))


class RecordingSink:
    def __init__(self, *, fatal: bool = False) -> None:
        self.payloads: list[dict[str, object]] = []
        self.fatal = fatal

    def write(self, payload: dict[str, object]) -> None:
        self.payloads.append(payload)
        if self.fatal:
            raise RuntimeError("sink unavailable")


class RecordingProvider:
    def __init__(self) -> None:
        self.list_calls: list[tuple[object, ...]] = []
        self.detail_calls: list[str] = []
        self.write_calls: list[str] = []
        self.detail_failures: dict[str, BaseException] = {}

    def query_my_bugs(
        self, *, scope_names: tuple[str, ...], page: int = 1, page_size: int = 20
    ) -> BugPage:
        self.list_calls.append(("personal", scope_names, page, page_size))
        pages = {1: (bug(1), bug(2)), 2: (bug(2), bug(3)), 3: (bug(4),)}
        return BugPage(
            items=pages.get(page, ()),
            coverage=Coverage(page=page, pageSize=2, total=5),
        )

    def query_user_bugs(
        self,
        user: str,
        *,
        scope_names: tuple[str, ...],
        page: int = 1,
        page_size: int = 20,
        browse_type: str | None = None,
    ) -> BugPage:
        self.list_calls.append((user, scope_names, page, page_size, browse_type))
        values = {
            ("alice", 1): (1, 2),
            ("alice", 2): (3,),
            ("bob", 1): (2, 4),
            ("bob", 2): (5,),
        }
        return BugPage(
            items=tuple(bug(x) for x in values.get((user, page), ())),
            coverage=Coverage(page=page, pageSize=2, total=3),
        )

    def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
        key = str(bug_id)
        self.detail_calls.append(key)
        failure = self.detail_failures.get(key)
        if failure is not None:
            raise failure
        return bug(int(key))

    def query_bug_history(
        self, bug_id: int | str, *, page: int = 1, page_size: int = 20
    ) -> HistoryPage:
        return HistoryPage(items=(), coverage=Coverage(total=0))

    def _write(self, name: str) -> NoReturn:
        self.write_calls.append(name)
        raise AssertionError(f"runtime called write port {name}")

    def add_bug_comment(self, *args: object, **kwargs: object) -> NoReturn:
        return self._write("add_bug_comment")

    def reconcile_comment(self, *args: object, **kwargs: object) -> NoReturn:
        return self._write("reconcile_comment")

    def update_bug_steps(self, *args: object, **kwargs: object) -> NoReturn:
        return self._write("update_bug_steps")

    def update_bug_steps_with_image(self, *args: object, **kwargs: object) -> NoReturn:
        return self._write("update_bug_steps_with_image")


def make_context(
    provider: RecordingProvider,
    ledger: RecordingLedger,
    *,
    limit: int = 10,
    sink: RecordingSink | None = None,
    dry_run: bool = False,
    readonly: bool = False,
    account: str | None = None,
) -> RunContext:
    config = AppConfig.model_validate(
        {
            "zentao": {"account": account},
            "personal": {"scopeNames": ["mine"]},
            "team": {"scopeNames": ["squad"], "members": ["alice", "bob"]},
            "limits": {"maxBugsPerRun": limit},
            "repositories": {},
        }
    )
    return RunContext(
        config,
        provider,
        ledger,
        lambda: datetime(2026, 7, 15, 0, 30),
        "owner",
        analysis=lambda *_: AnalysisSignal(evidenceComplete=True, fixCandidate=True),
        reportSink=sink,
        dryRun=dry_run,
        readonly=readonly,
    )


def test_personal_without_configured_account_uses_personal_scopes() -> None:
    provider, ledger = RecordingProvider(), RecordingLedger()
    result = run_personal(make_context(provider, ledger))
    assert provider.list_calls == [
        ("personal", ("mine",), 1, 10),
        ("personal", ("mine",), 2, 10),
        ("personal", ("mine",), 3, 10),
    ]
    assert provider.detail_calls == ["1", "2", "3", "4"]
    assert result.scopeNames == ("mine",) and result.members == ()


def test_personal_configured_account_discovers_assignee_without_remote_scope_filter() -> (
    None
):
    provider, ledger = RecordingProvider(), RecordingLedger()
    run_personal(make_context(provider, ledger, account="alice"))
    assert provider.list_calls == [
        ("alice", (), 1, 10, "assigntome"),
        ("alice", (), 2, 10, "assigntome"),
    ]


def test_report_discovery_uses_stable_official_page_size() -> None:
    provider, ledger = RecordingProvider(), RecordingLedger()
    run_personal(make_context(provider, ledger, limit=50, account="alice"))
    assert provider.list_calls == [
        ("alice", (), 1, 50, "assigntome"),
        ("alice", (), 2, 50, "assigntome"),
    ]


def test_team_deduplicates_across_members_and_applies_one_global_limit() -> None:
    provider, ledger = RecordingProvider(), RecordingLedger()
    result = run_team_report(make_context(provider, ledger, limit=4))
    assert provider.detail_calls == ["1", "2", "3", "4"]
    assert result.coverage == 4 and result.coverageTotal == 6 and result.truncated
    assert result.completeness == "PARTIAL"
    assert all(call[1] == ("squad",) for call in provider.list_calls)
    assert all(call[4] is None for call in provider.list_calls)
    assert result.members == ("alice", "bob") and provider.write_calls == []


def test_shared_shanghai_snapshot_and_payloads_are_identical() -> None:
    provider, ledger, sink = RecordingProvider(), RecordingLedger(), RecordingSink()
    result = run_personal(make_context(provider, ledger, sink=sink))
    payload = result.to_v2_payload()
    assert result.businessDate == "2026-07-15"
    assert result.snapshotCutoff == "2026-07-15T00:30:00+08:00"
    assert ledger.acquisitions[0][0] == ledger.checkpoints[0][0]
    assert ledger.checkpoints[0][2] == sink.payloads[0] == payload


def test_lease_unavailable_skips_work_and_success_releases() -> None:
    provider, unavailable = RecordingProvider(), RecordingLedger(acquired=False)
    result = run_personal(make_context(provider, unavailable))
    assert (
        result.completeness == "FAILED"
        and result.failures[0].category == "LEASE_UNAVAILABLE"
    )
    assert provider.list_calls == [] and unavailable.releases == []

    class CompleteProvider(RecordingProvider):
        def routed_bug(self, value: int) -> BugSnapshot:
            return BugSnapshot(
                id=value,
                status="active",
                version="v1",
                snapshotVersion="v1",
                routing=RoutingData(
                    repositories=("example-repo",),
                    selectedRepository="example-repo",
                    layer="frontend",
                    confidence="high",
                ),
            )

        def query_my_bugs(
            self, *, scope_names: tuple[str, ...], page: int = 1, page_size: int = 20
        ) -> BugPage:
            self.list_calls.append(("personal", scope_names, page, page_size))
            values = {1: (1, 2), 2: (3, 4)}
            return BugPage(
                items=tuple(self.routed_bug(x) for x in values.get(page, ())),
                coverage=Coverage(page=page, pageSize=2, total=4),
            )

        def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
            return self.routed_bug(int(bug_id))

    provider, ledger = CompleteProvider(), RecordingLedger()
    run_personal(make_context(provider, ledger))
    assert ledger.releases == [("lease", RunStatus.SUCCEEDED)]


def test_per_bug_failure_continues_and_payload_records_partial_result() -> None:
    provider, ledger, sink = RecordingProvider(), RecordingLedger(), RecordingSink()
    provider.detail_failures["2"] = ValueError("broken detail")
    result = run_personal(make_context(provider, ledger, sink=sink))
    assert provider.detail_calls == ["1", "2", "3", "4"]
    assert [item.bugId for item in result.bugResults] == ["1", "3", "4"]
    assert [(item.bugId, item.category) for item in result.failures] == [
        ("2", "ValueError")
    ]
    assert result.completeness == "PARTIAL"
    assert ledger.releases == [("lease", RunStatus.FAILED)]
    assert ledger.checkpoints[0][2] == sink.payloads[0] == result.to_v2_payload()


def test_history_capability_gap_retains_discovered_bugs_for_walkthrough() -> None:
    class NoHistoryProvider(RecordingProvider):
        def query_bug_history(
            self, bug_id: int | str, *, page: int = 1, page_size: int = 20
        ) -> HistoryPage:
            raise RuntimeError("history unsupported")

    result = run_personal(make_context(NoHistoryProvider(), RecordingLedger()))
    assert [item.bugId for item in result.bugResults] == ["1", "2", "3", "4"]
    assert all(
        item.decision.value == "NEEDS_ENGINEER_REVIEW" for item in result.bugResults
    )
    assert [(item.bugId, item.category) for item in result.failures] == [
        ("1", "RuntimeError"),
        ("2", "RuntimeError"),
        ("3", "RuntimeError"),
        ("4", "RuntimeError"),
    ]
    assert result.completeness == "PARTIAL"


@pytest.mark.parametrize("fatal", [KeyboardInterrupt(), SystemExit()])
def test_control_flow_exceptions_propagate_and_release(fatal: BaseException) -> None:
    provider, ledger = RecordingProvider(), RecordingLedger()
    provider.detail_failures["2"] = fatal
    with pytest.raises(type(fatal)):
        run_personal(make_context(provider, ledger))
    assert ledger.releases == [("lease", RunStatus.FAILED)]


def test_outer_fatal_releases_and_readonly_modes_never_write_provider() -> None:
    provider, ledger = RecordingProvider(), RecordingLedger()
    with pytest.raises(RuntimeError, match="sink unavailable"):
        run_team_report(
            make_context(
                provider,
                ledger,
                sink=RecordingSink(fatal=True),
                dry_run=True,
                readonly=True,
            )
        )
    assert ledger.releases == [("lease", RunStatus.FAILED)]
    assert provider.write_calls == []


@pytest.mark.parametrize("total", [0, 1])
def test_unknown_or_inconsistent_provider_coverage_is_partial(total: int) -> None:
    class InconsistentProvider(RecordingProvider):
        def query_my_bugs(
            self, *, scope_names: tuple[str, ...], page: int = 1, page_size: int = 20
        ) -> BugPage:
            self.list_calls.append(("personal", scope_names, page, page_size))
            return BugPage(items=(bug(1), bug(2)), coverage=Coverage(total=total))

    result = run_personal(make_context(InconsistentProvider(), RecordingLedger()))
    assert (
        result.coverageTotal is None
        and result.truncated
        and result.completeness == "PARTIAL"
    )


def test_personal_enriches_missing_routing_and_retains_ambiguous_bug() -> None:
    class TitleProvider(RecordingProvider):
        def query_my_bugs(
            self, *, scope_names: tuple[str, ...], page: int = 1, page_size: int = 20
        ) -> BugPage:
            self.list_calls.append(("personal", scope_names, page, page_size))
            return BugPage(
                items=(
                    BugSnapshot(
                        id=10,
                        status="active",
                        version="v1",
                        snapshotVersion="v1",
                        title="【Synthetic Area】 failure",
                        steps="button cannot click",
                    ),
                    BugSnapshot(
                        id=11,
                        status="active",
                        version="v1",
                        snapshotVersion="v1",
                        title="【Synthetic Area】 unclear failure",
                    ),
                ),
                coverage=Coverage(page=1, pageSize=20, total=2, pages=1),
            )

        def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
            return next(
                item
                for item in self.query_my_bugs(scope_names=("mine",)).items
                if str(item.id) == str(bug_id)
            )

    config = AppConfig.model_validate(
        {
            "personal": {"scopeNames": ["area-web", "area-api"]},
            "team": {"scopeNames": ["area-web"], "members": []},
            "repositories": {
                "area-web": {
                    "repository": "area-web",
                    "path": "repos/web",
                    "targetBranch": "feature/fix",
                    "testCommands": ["pytest"],
                },
                "area-api": {
                    "repository": "area-api",
                    "path": "repos/api",
                    "targetBranch": "feature/fix",
                    "testCommands": ["pytest"],
                },
            },
            "titleRouting": [
                {
                    "marker": "【Synthetic Area】",
                    "frontendRepository": "area-web",
                    "backendRepository": "area-api",
                }
            ],
        }
    )
    provider, ledger = TitleProvider(), RecordingLedger()
    context = RunContext(
        config,
        provider,
        ledger,
        lambda: datetime(2026, 7, 20, 9, 0),
        "owner",
        analysis=lambda *_: AnalysisSignal(evidenceComplete=True, fixCandidate=True),
    )
    result = run_personal(context)
    assert [item.bugId for item in result.bugResults] == ["10", "11"]
    assert result.bugResults[0].selectedRepository == "area-web"
    assert result.bugResults[0].layer == "frontend"
    assert result.bugResults[0].routingStatus == "ROUTED"
    assert result.to_v2_payload()["bugResults"][0]["candidates"] == [
        "area-web",
    ]  # type: ignore[index]
    assert result.bugResults[1].selectedRepository is None
    assert result.bugResults[1].decision.value == "NEEDS_ENGINEER_REVIEW"
    assert result.bugResults[1].routingStatus == "UNKNOWN"
    assert result.completeness == "PARTIAL"
