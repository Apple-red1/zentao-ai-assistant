from __future__ import annotations

from collections.abc import Sequence

from .models import AnalysisPhase, AnalysisSignal, BugAnalysisResult, Decision


def analyze_bug(
    snapshot: object,
    history: Sequence[object],
    phase: AnalysisPhase,
    *,
    signal: AnalysisSignal | None = None,
) -> BugAnalysisResult:
    del snapshot, history
    value = signal or AnalysisSignal()
    if phase is AnalysisPhase.PRECHECK:
        if value.toolOrPermissionGap:
            return BugAnalysisResult(Decision.TOOL_OR_PERMISSION_GAP, phase)
        if value.needsReporterInfo:
            return BugAnalysisResult(Decision.NEEDS_REPORTER_INFO, phase)
        if value.needsEngineerReview:
            return BugAnalysisResult(Decision.NEEDS_ENGINEER_REVIEW, phase)
        return BugAnalysisResult(Decision.PROCEED_TO_EVIDENCE, phase)
    if value.toolOrPermissionGap:
        decision = Decision.TOOL_OR_PERMISSION_GAP
    elif value.needsReporterInfo:
        decision = Decision.NEEDS_REPORTER_INFO
    elif value.needsEngineerReview:
        decision = Decision.NEEDS_ENGINEER_REVIEW
    elif not value.evidenceComplete:
        decision = Decision.NEEDS_REPORTER_INFO
    elif value.patchRetained:
        decision = Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION
    elif value.fixCandidate:
        decision = Decision.FIX_CANDIDATE
    else:
        decision = Decision.NEEDS_ENGINEER_REVIEW
    return BugAnalysisResult(decision, phase)
