from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import pytest

from zentao_ai.config.models import AppConfig
from zentao_ai.reporting.renderer import render_resolution_comment
from zentao_ai.safety.actions import AuthorizationRecord
from zentao_ai.state.models import OutboxRecord, OutboxStatus
from zentao_ai.workflows import repair_bug
from zentao_ai.workflows.models import (
    AnalysisPhase,
    AnalysisSignal,
    Decision,
    PatchOutcome,
    ResolutionCommentPayload,
    RunContext,
    TestResult as WorkflowTestResult,
)
from zentao_ai.zentao.models import (
    BugHistoryEntry,
    BugSnapshot,
    CommentWriteResult,
    Coverage,
    HistoryPage,
)


class RecordingProvider:
    def __init__(self, calls, snapshots, histories=((), ())):
        self.calls = calls
        self.snapshots = list(snapshots)
        self.histories = list(histories)
        self.comment_status = "CREATED"
        self.fail_at = None

    def _raise(self, name):
        if self.fail_at == name:
            raise RuntimeError(name)

    def query_bug_detail(self, bug_id):
        name = "snapshot" if len(self.snapshots) > 1 else "fresh_snapshot"
        self.calls.append(name)
        self._raise(name)
        return self.snapshots.pop(0)

    def query_bug_history(self, bug_id, *, page=1, page_size=20):
        name = "history" if len(self.histories) > 1 else "fresh_history"
        self.calls.append(name)
        self._raise(name)
        return HistoryPage(
            items=tuple(self.histories.pop(0)), coverage=Coverage(total=0)
        )

    def add_bug_comment(self, bug_id, comment, confirm, idempotency_key):
        self.calls.append("comment")
        self._raise("comment")
        return CommentWriteResult(
            created=self.comment_status == "CREATED",
            alreadyExists=self.comment_status == "ALREADY_EXISTS",
            status=self.comment_status,
        )

    def reconcile_comment(self, idempotency_key, bug_id, *, comment=None):
        self.calls.append("reconcile")
        return CommentWriteResult(created=False, alreadyExists=False, status="UNKNOWN")


class RecordingLedger:
    def __init__(self, calls):
        self.calls = calls
        self.outbox_status = OutboxStatus.PENDING

    def put_outbox(self, record):
        self.calls.append("outbox")
        return replace(record, status=self.outbox_status)

    def mark_outbox_result(self, key, status, external_id):
        self.calls.append(("outbox_result", status))
        return OutboxRecord(key, "comment", {}, status)

    def reconcile_outbox(self, key, status, external_id):
        self.calls.append(("outbox_reconcile", status))
        return OutboxRecord(key, "comment", {}, status)


class RecordingRepository:
    def __init__(self, calls):
        self.calls = calls
        self.allowed = True
        self.include_confined = True
        self.confined = True
        self.unchanged_result = True
        self.fail_at = None

    def preflight(self, config, routing):
        self.calls.append("preflight")
        if self.fail_at == "preflight":
            raise RuntimeError("preflight")
        fields = {"allowed": self.allowed}
        if self.include_confined:
            fields["confined"] = self.confined
        return type("Lease", (), fields)()

    def unchanged(self, lease):
        self.calls.append("repository_unchanged")
        if self.fail_at == "repository_unchanged":
            raise RuntimeError("repository_unchanged")
        return self.unchanged_result


class RecordingPatchExecutor:
    def __init__(self, calls):
        self.calls = calls
        self.reproduced = False
        self.outcome = PatchOutcome.APPLIED
        self.tests_passed = True
        self.safe = True
        self.fail_at = None

    def _call(self, name, result):
        self.calls.append(name)
        if self.fail_at == name:
            raise RuntimeError(name)
        return result

    def reproduce(self, repository, bug):
        return self._call("repro", self.reproduced)

    def apply(self, repository, bug):
        return self._call("apply", self.outcome)

    def test(self, repository, commands):
        self.calls.append(("tests", tuple(commands)))
        if self.fail_at == "tests":
            raise RuntimeError("tests")
        return self.tests_passed

    def diff_safe(self, repository):
        return self._call("diff", self.safe)

    def __getattr__(self, name):
        if name in {"checkout", "commit", "push", "merge", "deploy", "reset", "resolve", "close"}:
            raise AssertionError(f"prohibited PatchExecutor operation accessed: {name}")
        raise AttributeError(name)


def bug(**changes):
    values = dict(
        id=7,
        status="active",
        assignee="alice",
        version="v1",
        snapshotVersion="s1",
        routing={
            "repositories": ["repo"],
            "selectedRepository": "repo",
            "confidence": "high",
        },
    )
    values.update(changes)
    return BugSnapshot(**values)


def harness(*, final_candidate=True, snapshots=None, histories=((), ())):
    calls = []
    snapshots = snapshots or (bug(), bug())
    provider = RecordingProvider(calls, snapshots, histories)
    ledger = RecordingLedger(calls)
    repository = RecordingRepository(calls)
    patch = RecordingPatchExecutor(calls)
    config = AppConfig.model_validate(
        {
            "personal": {"scopeNames": ["mine"]},
            "team": {"scopeNames": ["team"]},
            "repositories": {
                "main": {
                    "repository": "repo",
                    "path": "C:/repo",
                    "targetBranch": "main",
                    "testCommands": ["pytest -q", "ruff check ."],
                }
            },
            "permissions": {"codeWriteEnabled": True, "commentEnabled": True},
        }
    )

    def analysis(snapshot, history, phase):
        calls.append("precheck" if phase is AnalysisPhase.PRECHECK else "final")
        return AnalysisSignal(
            evidenceComplete=True,
            fixCandidate=phase is AnalysisPhase.FINAL and final_candidate,
            needsEngineerReview=phase is AnalysisPhase.FINAL and not final_candidate,
        )

    tests = (
        WorkflowTestResult("pytest -q", True),
        WorkflowTestResult("ruff check .", True),
    )
    body = render_resolution_comment(
        ResolutionCommentPayload(
            summary=(
                "Local patch passed the configured validation and remains an "
                "uncommitted candidate for human review."
            ),
            testResults=tests,
        )
    )
    context = RunContext(
        config,
        provider,
        ledger,
        lambda: datetime(2026, 7, 15, 9),
        "owner",
        analysis=analysis,
        repository=repository,
        patchExecutor=patch,
        currentTurnId="turn-1",
        authorizationRecords=(
            AuthorizationRecord(
                turnId="turn-1",
                source="user",
                action="comment",
                bugId="7",
                parameters={"comment": body},
            ),
        ),
        snapshotStable=True,
        historyChecked=True,
        cooldownPassed=True,
        idempotencyPassed=True,
    )
    return context, provider, ledger, repository, patch, calls


def test_happy_path_has_strict_order_exact_whitelist_and_no_prohibited_operations():
    context, _, _, _, patch, calls = harness()
    result = repair_bug(context, 7)
    assert result.decision is Decision.FIX_CANDIDATE
    assert (result.localCandidateSuccess, result.success, result.commentDelivered) == (
        True,
        True,
        True,
    )
    assert result.localChangesRetained
    assert [x.command for x in result.testResults] == ["pytest -q", "ruff check ."]
    assert calls == [
        "snapshot",
        "history",
        "precheck",
        "preflight",
        "repro",
        "apply",
        ("tests", ("pytest -q", "ruff check .")),
        "diff",
        "fresh_snapshot",
        "fresh_history",
        "repository_unchanged",
        "final",
        "outbox",
        "comment",
        ("outbox_result", OutboxStatus.CREATED),
    ]
    for name in ("checkout", "commit", "push", "merge", "deploy", "reset", "resolve", "close"):
        with pytest.raises(AssertionError):
            getattr(patch, name)


@pytest.mark.parametrize("readonly,dry_run", [(True, False), (False, True)])
def test_dryrun_and_readonly_do_not_touch_provider_or_patch(readonly, dry_run):
    context, *_rest, calls = harness()
    context = replace(context, readonly=readonly, dryRun=dry_run)
    result = repair_bug(context, 7)
    assert result.decision is Decision.TOOL_OR_PERMISSION_GAP
    assert calls == []


def assert_stopped(result, calls, expected_calls, *, retained=False, tests=()):
    assert calls == expected_calls
    assert result.success is False
    assert result.localCandidateSuccess is False
    assert result.commentDelivered is False
    assert result.localChangesRetained is retained
    assert result.testResults == tests
    assert result.commentResult is None
    assert not any(
        call in {"checkout", "commit", "push", "merge", "deploy", "reset", "resolve", "close"}
        for call in calls
        if isinstance(call, str)
    )


def test_precheck_nonproceed_stops_before_routing_and_preserves_decision():
    context, _, _, _, _, calls = harness()

    def recheck(snapshot, history, phase):
        calls.append("precheck")
        return AnalysisSignal(needsReporterInfo=True)

    result = repair_bug(replace(context, analysis=recheck), 7)
    assert result.decision is Decision.NEEDS_REPORTER_INFO
    assert_stopped(result, calls, ["snapshot", "history", "precheck"])


@pytest.mark.parametrize("missing", ["repository", "patchExecutor"])
def test_each_required_port_missing_stops_before_preflight(missing):
    context, _, _, _, _, calls = harness()
    result = repair_bug(replace(context, **{missing: None}), 7)
    assert result.reasons == ("PORT_NOT_CONFIGURED",)
    assert_stopped(result, calls, ["snapshot", "history", "precheck"])


@pytest.mark.parametrize("mode", ["unconfigured", "empty_whitelist"])
def test_repository_mapping_and_whitelist_are_required(mode):
    context, _, _, _, _, calls = harness()
    repositories = {} if mode == "unconfigured" else {
        "main": context.config.repositories["main"].model_copy(update={"testCommands": []})
    }
    config = context.config.model_copy(update={"repositories": repositories})
    result = repair_bug(replace(context, config=config), 7)
    assert result.reasons == ("TEST_WHITELIST_REQUIRED",)
    assert_stopped(result, calls, ["snapshot", "history", "precheck"])


@pytest.mark.parametrize(
    "allowed,include_confined,confined,reason",
    [
        (False, True, True, "REPOSITORY_LEASE_DENIED"),
        (True, True, False, "REPOSITORY_CONFINEMENT_FAILED"),
        (True, False, True, "REPOSITORY_CONFINEMENT_FAILED"),
    ],
)
def test_incomplete_or_denied_lease_fails_closed_before_reproduction(
    allowed, include_confined, confined, reason
):
    context, _, _, repository, _, calls = harness()
    repository.allowed = allowed
    repository.include_confined = include_confined
    repository.confined = confined
    result = repair_bug(context, 7)
    assert result.reasons == (reason,)
    assert_stopped(
        result, calls, ["snapshot", "history", "precheck", "preflight"]
    )


def test_reproduction_must_fail_before_patch_application():
    context, _, _, _, patch, calls = harness()
    patch.reproduced = True
    result = repair_bug(context, 7)
    assert result.reasons == ("REPRODUCTION_DID_NOT_FAIL",)
    assert_stopped(
        result,
        calls,
        ["snapshot", "history", "precheck", "preflight", "repro"],
    )


def test_failed_patch_outcome_retains_possible_changes_and_stops():
    context, _, _, _, patch, calls = harness()
    patch.outcome = PatchOutcome.FAILED
    result = repair_bug(context, 7)
    assert result.reasons == ("PATCH_APPLICATION_FAILED",)
    assert_stopped(
        result,
        calls,
        ["snapshot", "history", "precheck", "preflight", "repro", "apply"],
        retained=True,
    )


def test_unsafe_diff_retains_patch_without_fresh_reads_or_comment():
    context, _, _, _, patch, calls = harness()
    patch.safe = False
    result = repair_bug(context, 7)
    expected_tests = tuple(
        WorkflowTestResult(command, True) for command in ("pytest -q", "ruff check .")
    )
    assert result.reasons == ("UNSAFE_DIFF",)
    assert_stopped(
        result,
        calls,
        [
            "snapshot", "history", "precheck", "preflight", "repro", "apply",
            ("tests", ("pytest -q", "ruff check .")), "diff",
        ],
        retained=True,
        tests=expected_tests,
    )


def test_candidate_comment_skipped_is_not_delivery_or_overall_success():
    context, *_rest, calls = harness()
    context = replace(context, authorizationRecords=())
    result = repair_bug(context, 7)
    assert result.decision is Decision.FIX_CANDIDATE
    assert result.localCandidateSuccess and result.localChangesRetained
    assert not result.commentDelivered and not result.success
    assert result.commentResult is not None and result.commentResult.status == "SKIPPED"
    assert calls[-1] == "final"


@pytest.mark.parametrize(
    "routing",
    [
        None,
        {"repositories": [], "selectedRepository": None, "confidence": "none"},
        {"repositories": ["a", "b"], "selectedRepository": "a", "confidence": "high"},
        {"repositories": ["repo"], "selectedRepository": "repo", "confidence": "none"},
    ],
)
def test_untrusted_routing_stops_before_repository(routing):
    context, *_rest, calls = harness(snapshots=(bug(routing=routing), bug()))
    result = repair_bug(context, 7)
    assert result.reasons == ("ROUTING_NOT_TRUSTED",)
    assert_stopped(result, calls, ["snapshot", "history", "precheck"])


@pytest.mark.parametrize(
    "stage,reason",
    [
        ("snapshot", "SNAPSHOT_QUERY_FAILED"),
        ("history", "HISTORY_QUERY_FAILED"),
        ("preflight", "REPOSITORY_PREFLIGHT_FAILED"),
        ("repro", "REPRODUCTION_FAILED"),
        ("apply", "PATCH_APPLICATION_FAILED"),
        ("tests", "TEST_EXECUTION_FAILED"),
        ("diff", "DIFF_VALIDATION_FAILED"),
        ("fresh_snapshot", "FRESH_SNAPSHOT_QUERY_FAILED"),
        ("repository_unchanged", "REPOSITORY_VALIDATION_FAILED"),
        ("fresh_history", "FRESH_HISTORY_QUERY_FAILED"),
        ("comment", "COMMENT_DELIVERY_FAILED"),
    ],
)
def test_all_operational_errors_are_classified(stage, reason):
    context, provider, _, repository, patch, _ = harness()
    if stage in {"snapshot", "history", "fresh_snapshot", "fresh_history", "comment"}:
        provider.fail_at = stage
    elif stage in {"preflight", "repository_unchanged"}:
        repository.fail_at = stage
    else:
        patch.fail_at = stage
    result = repair_bug(context, 7)
    assert result.reasons == (reason,)
    assert not result.success


@pytest.mark.parametrize("exc", [KeyboardInterrupt(), SystemExit()])
def test_control_flow_exceptions_propagate(exc):
    context, provider, *_ = harness()

    def stop(_bug_id):
        raise exc

    provider.query_bug_detail = stop
    with pytest.raises(type(exc)):
        repair_bug(context, 7)


def test_tests_failed_outcome_still_runs_whitelist_and_retains_without_comment():
    context, _, _, _, patch, calls = harness()
    patch.outcome = PatchOutcome.TESTS_FAILED
    patch.tests_passed = False
    result = repair_bug(context, 7)
    assert result.decision is Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION
    assert result.localChangesRetained and not result.localCandidateSuccess
    assert result.testResults and not any(x.passed for x in result.testResults)
    assert ("tests", ("pytest -q", "ruff check .")) in calls
    assert "comment" not in calls


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ({"snapshotVersion": "s2"}, "SNAPSHOT_VERSION_CHANGED"),
        ({"status": "resolved"}, "STATUS_CHANGED"),
        ({"assignee": "bob"}, "ASSIGNEE_CHANGED"),
    ],
)
def test_snapshot_drift_retains_patch_and_stops_before_final(mutation, reason):
    context, *_rest, calls = harness(snapshots=(bug(), bug(**mutation)))
    result = repair_bug(context, 7)
    assert result.reasons == (reason,)
    assert result.localChangesRetained and "final" not in calls


def test_history_and_repository_drift_are_classified():
    entry = BugHistoryEntry(id=1, action="edited")
    context, *_rest, calls = harness(histories=((), (entry,)))
    result = repair_bug(context, 7)
    assert result.reasons == ("HISTORY_CHANGED",) and "final" not in calls
    context, _, _, repository, _, calls = harness()
    repository.unchanged_result = False
    result = repair_bug(context, 7)
    assert result.reasons == ("REPOSITORY_CHANGED",) and "final" not in calls


@pytest.mark.parametrize(
    "status,delivered,success",
    [
        (OutboxStatus.CREATED, True, True),
        (OutboxStatus.ALREADY_EXISTS, True, True),
        (OutboxStatus.FAILED, False, False),
        (OutboxStatus.UNKNOWN, False, False),
    ],
)
def test_comment_result_controls_delivery_and_overall_success(status, delivered, success):
    context, _, ledger, *_ = harness()
    ledger.outbox_status = status
    result = repair_bug(context, 7)
    assert result.localCandidateSuccess
    assert result.commentDelivered is delivered and result.success is success
    assert result.commentResult is not None and result.commentResult.status == status.value


def test_final_noncandidate_retains_without_candidate_comment():
    context, *_rest, calls = harness(final_candidate=False)
    result = repair_bug(context, 7)
    assert result.decision is Decision.NEEDS_ENGINEER_REVIEW
    assert result.localChangesRetained and not result.localCandidateSuccess
    assert result.commentResult is None and "comment" not in calls
