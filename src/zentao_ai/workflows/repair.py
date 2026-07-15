from __future__ import annotations

from .analysis import analyze_bug
from .models import AnalysisPhase, Decision, PatchOutcome, RepairResult, RunContext
from .models import ResolutionCommentPayload, TestResult
from .comments import write_resolution_comment


def repair_bug(context: RunContext, bug_id: int | str) -> RepairResult:
    if (
        context.dryRun
        or context.readonly
        or not context.config.permissions.codeWriteEnabled
    ):
        return RepairResult(
            str(bug_id),
            Decision.TOOL_OR_PERMISSION_GAP,
            reasons=("CODE_WRITE_DISABLED",),
        )
    first = context.provider.query_bug_detail(bug_id)
    history = context.provider.query_bug_history(bug_id, page=1, page_size=100).items
    pre = analyze_bug(
        first,
        history,
        AnalysisPhase.PRECHECK,
        signal=context.analysis(first, history, AnalysisPhase.PRECHECK)
        if context.analysis
        else None,
    )
    if (
        pre.decision is not Decision.PROCEED_TO_EVIDENCE
        or first.routing is None
        or first.routing.selected_repository is None
        or first.routing.confidence != 1.0
        or len(first.routing.repositories) != 1
    ):
        return RepairResult(
            str(bug_id),
            Decision.TOOL_OR_PERMISSION_GAP,
            reasons=("ROUTING_NOT_TRUSTED",),
        )
    if context.repository is None or context.patchExecutor is None:
        return RepairResult(
            str(bug_id),
            Decision.TOOL_OR_PERMISSION_GAP,
            reasons=("PORT_NOT_CONFIGURED",),
        )
    try:
        lease = context.repository.preflight(context.config, first.routing)
    except Exception:
        return RepairResult(
            str(bug_id),
            Decision.TOOL_OR_PERMISSION_GAP,
            reasons=("REPOSITORY_PREFLIGHT_FAILED",),
        )
    if getattr(lease, "allowed", True) is False:
        return RepairResult(
            str(bug_id),
            Decision.TOOL_OR_PERMISSION_GAP,
            reasons=("REPOSITORY_PREFLIGHT_FAILED",),
        )
    selected = first.routing.selected_repository
    mappings = [
        value
        for value in context.config.repositories.values()
        if value.repository == selected
    ]
    if len(mappings) != 1 or not mappings[0].testCommands:
        return RepairResult(
            str(bug_id),
            Decision.TOOL_OR_PERMISSION_GAP,
            reasons=("TEST_WHITELIST_REQUIRED",),
        )
    if context.patchExecutor.reproduce(lease, first):
        return RepairResult(
            str(bug_id),
            Decision.NEEDS_ENGINEER_REVIEW,
            reasons=("REPRODUCTION_DID_NOT_FAIL",),
        )
    outcome = context.patchExecutor.apply(lease, first)
    if outcome is PatchOutcome.FAILED:
        return RepairResult(
            str(bug_id),
            Decision.NEEDS_ENGINEER_REVIEW,
            reasons=("PATCH_APPLICATION_FAILED",),
        )
    tests_passed = (
        context.patchExecutor.test(lease, tuple(mappings[0].testCommands))
        if outcome is PatchOutcome.APPLIED
        else False
    )
    test_results = tuple(
        TestResult(command, tests_passed) for command in mappings[0].testCommands
    )
    diff_safe = context.patchExecutor.diff_safe(lease)
    if not tests_passed or not diff_safe:
        return RepairResult(
            str(bug_id),
            Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION,
            localChangesRetained=True,
            reasons=("TEST_OR_DIFF_VALIDATION_FAILED",),
            testResults=test_results,
        )
    second = context.provider.query_bug_detail(bug_id)
    if (
        second.snapshot_version != first.snapshot_version
        or second.status != first.status
        or second.assignee != first.assignee
        or not context.repository.unchanged(lease)
    ):
        drift = (
            "SNAPSHOT_VERSION_CHANGED"
            if second.snapshot_version != first.snapshot_version
            else "STATUS_CHANGED"
            if second.status != first.status
            else "ASSIGNEE_CHANGED"
            if second.assignee != first.assignee
            else "REPOSITORY_CHANGED"
        )
        return RepairResult(
            str(bug_id),
            Decision.NEEDS_ENGINEER_REVIEW,
            localChangesRetained=True,
            reasons=(drift,),
            testResults=test_results,
        )
    fresh_history = context.provider.query_bug_history(
        bug_id, page=1, page_size=100
    ).items
    if fresh_history != history:
        return RepairResult(
            str(bug_id),
            Decision.NEEDS_ENGINEER_REVIEW,
            localChangesRetained=True,
            reasons=("HISTORY_CHANGED",),
            testResults=test_results,
        )
    final = analyze_bug(
        second,
        fresh_history,
        AnalysisPhase.FINAL,
        signal=context.analysis(second, fresh_history, AnalysisPhase.FINAL)
        if context.analysis
        else None,
    )
    comment_result = None
    if final.decision is Decision.FIX_CANDIDATE:
        comment_result = write_resolution_comment(
            context,
            second,
            ResolutionCommentPayload(
                summary=(
                    "Local patch passed the configured validation and remains an "
                    "uncommitted candidate for human review."
                ),
                testResults=test_results,
            ),
        )
    local_candidate = final.decision is Decision.FIX_CANDIDATE
    comment_delivered = comment_result is not None and comment_result.status in {
        "CREATED",
        "ALREADY_EXISTS",
    }
    return RepairResult(
        str(bug_id),
        final.decision,
        success=local_candidate and comment_delivered,
        localCandidateSuccess=local_candidate,
        commentDelivered=comment_delivered,
        localChangesRetained=True,
        commentResult=comment_result,
        testResults=test_results,
    )
