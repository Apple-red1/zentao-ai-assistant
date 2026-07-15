from __future__ import annotations

from .analysis import analyze_bug
from .models import AnalysisPhase, Decision, PatchOutcome, RepairResult, RunContext


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
    diff_safe = context.patchExecutor.diff_safe(lease)
    if not tests_passed or not diff_safe:
        return RepairResult(
            str(bug_id),
            Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION,
            localChangesRetained=True,
            reasons=("TEST_OR_DIFF_VALIDATION_FAILED",),
        )
    second = context.provider.query_bug_detail(bug_id)
    if (
        second.snapshot_version != first.snapshot_version
        or second.status != first.status
        or second.assignee != first.assignee
        or not context.repository.unchanged(lease)
    ):
        return RepairResult(
            str(bug_id),
            Decision.NEEDS_ENGINEER_REVIEW,
            localChangesRetained=True,
            reasons=("SNAPSHOT_CHANGED",),
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
        )
    final = analyze_bug(
        second,
        fresh_history,
        AnalysisPhase.FINAL,
        signal=context.analysis(second, fresh_history, AnalysisPhase.FINAL)
        if context.analysis
        else None,
    )
    return RepairResult(
        str(bug_id),
        final.decision,
        success=final.decision is Decision.FIX_CANDIDATE,
        localChangesRetained=True,
    )
