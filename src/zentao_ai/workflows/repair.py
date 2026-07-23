from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from zentao_ai.safety.actions import ActionRequest, AuthorizationContext
from zentao_ai.safety.authorization import authorize, has_exact_authorization

from .analysis import analyze_bug
from .comments import write_resolution_comment
from .models import (
    AnalysisPhase,
    Decision,
    PatchOutcome,
    RepairResult,
    ResolutionCommentPayload,
    RunContext,
    TestResult,
)
from .snapshot_guard import unstable_snapshot_matches


def _failure(
    bug_id: int | str,
    decision: Decision,
    reason: str,
    *,
    retained: bool = False,
    tests: tuple[TestResult, ...] = (),
) -> RepairResult:
    return RepairResult(
        str(bug_id),
        decision,
        localChangesRetained=retained,
        reasons=(reason,),
        testResults=tests,
    )


T = TypeVar("T")


def _attempt(operation: Callable[[], T]) -> tuple[bool, T | None]:
    """Run an external port operation without swallowing process control signals."""
    try:
        return True, operation()
    except Exception:
        return False, None


def repair_bug(context: RunContext, bug_id: int | str) -> RepairResult:
    """Produce a local, uncommitted repair candidate through safety-gated ports."""
    if context.dryRun or context.readonly or not context.config.permissions.codeWriteEnabled:
        return _failure(
            bug_id, Decision.TOOL_OR_PERMISSION_GAP, "CODE_WRITE_DISABLED"
        )

    ok, first = _attempt(
        lambda: context.provider.query_bug_detail(bug_id, allow_unstable=True)
    )
    if not ok:
        return _failure(bug_id, Decision.TOOL_OR_PERMISSION_GAP, "SNAPSHOT_QUERY_FAILED")
    assert first is not None
    if str(first.id) != str(bug_id):
        return _failure(
            bug_id, Decision.NEEDS_ENGINEER_REVIEW, "BUG_ID_MISMATCH"
        )
    snapshot_stable = context.snapshotStable and first.snapshot_stable
    write_action = ActionRequest(action="write_code", bugId=str(bug_id))
    authorization_context = AuthorizationContext(
        codeWriteEnabled=context.config.permissions.codeWriteEnabled,
        routingUnique=True,
        repositoryGuardPassed=True,
        snapshotStable=snapshot_stable,
        currentTurnId=context.currentTurnId,
        authorizationRecords=context.authorizationRecords,
    )
    if not snapshot_stable and (
        context.scheduled
        or not has_exact_authorization(write_action, authorization_context)
    ):
        return _failure(
            bug_id,
            Decision.TOOL_OR_PERMISSION_GAP,
            "CODE_WRITE_AUTHORIZATION_REQUIRED",
        )
    ok, history_page = _attempt(
        lambda: context.provider.query_bug_history(bug_id, page=1, page_size=100)
    )
    if not ok:
        return _failure(bug_id, Decision.TOOL_OR_PERMISSION_GAP, "HISTORY_QUERY_FAILED")
    assert history_page is not None
    history = history_page.items

    ok, pre = _attempt(
        lambda: analyze_bug(
            first,
            history,
            AnalysisPhase.PRECHECK,
            signal=context.analysis(first, history, AnalysisPhase.PRECHECK)
            if context.analysis
            else None,
        )
    )
    if not ok:
        return _failure(
            bug_id, Decision.NEEDS_ENGINEER_REVIEW, "PRECHECK_ANALYSIS_FAILED"
        )
    assert pre is not None
    if pre.decision is not Decision.PROCEED_TO_EVIDENCE:
        return RepairResult(
            str(bug_id),
            pre.decision,
            reasons=pre.reasons,
        )

    routing = first.routing
    if (
        routing is None
        or routing.selected_repository is None
        or routing.confidence != "high"
        or len(routing.repositories) != 1
        or routing.repositories[0] != routing.selected_repository
    ):
        return _failure(
            bug_id, Decision.TOOL_OR_PERMISSION_GAP, "ROUTING_NOT_TRUSTED"
        )
    if context.repository is None or context.patchExecutor is None:
        return _failure(bug_id, Decision.TOOL_OR_PERMISSION_GAP, "PORT_NOT_CONFIGURED")
    repository = context.repository
    patch_executor = context.patchExecutor

    selected = routing.selected_repository
    mappings = [
        value
        for value in context.config.repositories.values()
        if value.repository == selected
    ]
    if len(mappings) != 1 or not mappings[0].testCommands:
        return _failure(
            bug_id, Decision.TOOL_OR_PERMISSION_GAP, "TEST_WHITELIST_REQUIRED"
        )

    ok, lease = _attempt(lambda: repository.preflight(context.config, routing))
    if not ok or lease is None:
        return _failure(
            bug_id, Decision.TOOL_OR_PERMISSION_GAP, "REPOSITORY_PREFLIGHT_FAILED"
        )
    if getattr(lease, "allowed", False) is not True:
        return _failure(bug_id, Decision.TOOL_OR_PERMISSION_GAP, "REPOSITORY_LEASE_DENIED")
    if getattr(lease, "confined", False) is not True:
        return _failure(
            bug_id, Decision.TOOL_OR_PERMISSION_GAP, "REPOSITORY_CONFINEMENT_FAILED"
        )

    ok, reproduction_passed = _attempt(
        lambda: patch_executor.reproduce(lease, first)
    )
    if not ok:
        return _failure(
            bug_id, Decision.NEEDS_ENGINEER_REVIEW, "REPRODUCTION_FAILED"
        )
    if reproduction_passed:
        return _failure(
            bug_id, Decision.NEEDS_ENGINEER_REVIEW, "REPRODUCTION_DID_NOT_FAIL"
        )

    write_authorized = authorize(
        write_action,
        authorization_context,
    ).allowed
    if not write_authorized:
        return _failure(
            bug_id,
            Decision.TOOL_OR_PERMISSION_GAP,
            "CODE_WRITE_AUTHORIZATION_REQUIRED",
        )

    write_snapshot = first
    if not snapshot_stable:
        ok, guarded_snapshot = _attempt(
            lambda: context.provider.query_bug_detail(
                bug_id, allow_unstable=True
            )
        )
        if (
            not ok
            or guarded_snapshot is None
            or not unstable_snapshot_matches(first, guarded_snapshot)
        ):
            return _failure(
                bug_id,
                Decision.NEEDS_ENGINEER_REVIEW,
                "UNSTABLE_SNAPSHOT_CHANGED",
            )
        write_snapshot = guarded_snapshot

    ok, outcome = _attempt(lambda: patch_executor.apply(lease, write_snapshot))
    if not ok or outcome is PatchOutcome.FAILED:
        return _failure(
            bug_id,
            Decision.NEEDS_ENGINEER_REVIEW,
            "PATCH_APPLICATION_FAILED",
            retained=True,
        )

    commands = tuple(mappings[0].testCommands)
    ok, tests_passed = _attempt(lambda: patch_executor.test(lease, commands))
    if not ok:
        tests = tuple(TestResult(command, False) for command in commands)
        return _failure(
            bug_id,
            Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION,
            "TEST_EXECUTION_FAILED",
            retained=True,
            tests=tests,
        )
    tests = tuple(TestResult(command, bool(tests_passed)) for command in commands)
    if not tests_passed or outcome is PatchOutcome.TESTS_FAILED:
        return _failure(
            bug_id,
            Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION,
            "WHITELIST_TESTS_FAILED",
            retained=True,
            tests=tests,
        )

    ok, diff_safe = _attempt(lambda: patch_executor.diff_safe(lease))
    if not ok:
        return _failure(
            bug_id,
            Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION,
            "DIFF_VALIDATION_FAILED",
            retained=True,
            tests=tests,
        )
    if not diff_safe:
        return _failure(
            bug_id,
            Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION,
            "UNSAFE_DIFF",
            retained=True,
            tests=tests,
        )

    ok, second = _attempt(
        lambda: context.provider.query_bug_detail(
            bug_id, allow_unstable=not snapshot_stable
        )
    )
    if not ok:
        return _failure(
            bug_id,
            Decision.NEEDS_ENGINEER_REVIEW,
            "FRESH_SNAPSHOT_QUERY_FAILED",
            retained=True,
            tests=tests,
        )
    assert second is not None
    if second.snapshot_version != write_snapshot.snapshot_version:
        return _failure(bug_id, Decision.NEEDS_ENGINEER_REVIEW, "SNAPSHOT_VERSION_CHANGED", retained=True, tests=tests)
    if second.status != write_snapshot.status:
        return _failure(bug_id, Decision.NEEDS_ENGINEER_REVIEW, "STATUS_CHANGED", retained=True, tests=tests)
    if second.assignee != write_snapshot.assignee:
        return _failure(bug_id, Decision.NEEDS_ENGINEER_REVIEW, "ASSIGNEE_CHANGED", retained=True, tests=tests)

    ok, fresh_history_page = _attempt(
        lambda: context.provider.query_bug_history(bug_id, page=1, page_size=100)
    )
    if not ok:
        return _failure(bug_id, Decision.NEEDS_ENGINEER_REVIEW, "FRESH_HISTORY_QUERY_FAILED", retained=True, tests=tests)
    assert fresh_history_page is not None
    fresh_history = fresh_history_page.items
    if fresh_history != history:
        return _failure(bug_id, Decision.NEEDS_ENGINEER_REVIEW, "HISTORY_CHANGED", retained=True, tests=tests)

    ok, repository_unchanged = _attempt(lambda: repository.unchanged(lease))
    if not ok:
        return _failure(bug_id, Decision.NEEDS_ENGINEER_REVIEW, "REPOSITORY_VALIDATION_FAILED", retained=True, tests=tests)
    if not repository_unchanged:
        return _failure(bug_id, Decision.NEEDS_ENGINEER_REVIEW, "REPOSITORY_CHANGED", retained=True, tests=tests)

    ok, final = _attempt(
        lambda: analyze_bug(
            second,
            fresh_history,
            AnalysisPhase.FINAL,
            signal=context.analysis(second, fresh_history, AnalysisPhase.FINAL)
            if context.analysis
            else None,
        )
    )
    if not ok:
        return _failure(bug_id, Decision.NEEDS_ENGINEER_REVIEW, "FINAL_ANALYSIS_FAILED", retained=True, tests=tests)
    assert final is not None
    if final.decision is not Decision.FIX_CANDIDATE:
        return RepairResult(
            str(bug_id),
            final.decision,
            localChangesRetained=True,
            reasons=final.reasons,
            testResults=tests,
        )

    ok, comment = _attempt(
        lambda: write_resolution_comment(
            context,
            second,
            ResolutionCommentPayload(
                summary=(
                    "Local patch passed the configured validation and remains an "
                    "uncommitted candidate for human review."
                ),
                testResults=tests,
            ),
        )
    )
    if not ok:
        return RepairResult(
            str(bug_id),
            Decision.FIX_CANDIDATE,
            localCandidateSuccess=True,
            localChangesRetained=True,
            reasons=("COMMENT_DELIVERY_FAILED",),
            testResults=tests,
        )
    assert comment is not None
    delivered = comment.status in {"CREATED", "ALREADY_EXISTS"}
    return RepairResult(
        str(bug_id),
        Decision.FIX_CANDIDATE,
        success=delivered,
        localCandidateSuccess=True,
        commentDelivered=delivered,
        localChangesRetained=True,
        commentResult=comment,
        testResults=tests,
    )
