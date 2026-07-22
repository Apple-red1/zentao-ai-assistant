from __future__ import annotations

from collections.abc import Sequence

from .models import AnalysisPhase, AnalysisSignal, BugAnalysisResult, Decision
from .policy import default_analysis_signal


def _has_explicit_signal(value: AnalysisSignal) -> bool:
    return any(
        (
            value.evidenceComplete,
            value.fixCandidate,
            value.needsReporterInfo,
            value.needsEngineerReview,
            value.toolOrPermissionGap,
            value.patchRetained,
        )
    )


def analyze_bug(
    snapshot: object,
    history: Sequence[object],
    phase: AnalysisPhase,
    *,
    signal: AnalysisSignal | None = None,
) -> BugAnalysisResult:
    value = signal or AnalysisSignal()
    if not _has_explicit_signal(value):
        value = default_analysis_signal(snapshot, history, phase)
    if phase is AnalysisPhase.PRECHECK:
        if value.toolOrPermissionGap:
            return BugAnalysisResult(Decision.TOOL_OR_PERMISSION_GAP, phase)
        if value.needsEngineerReview:
            return BugAnalysisResult(Decision.NEEDS_ENGINEER_REVIEW, phase)
        if value.needsReporterInfo:
            return BugAnalysisResult(Decision.NEEDS_REPORTER_INFO, phase)
        return BugAnalysisResult(Decision.PROCEED_TO_EVIDENCE, phase)
    if value.toolOrPermissionGap:
        decision = Decision.TOOL_OR_PERMISSION_GAP
    elif value.patchRetained:
        decision = Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION
    elif value.needsEngineerReview:
        decision = Decision.NEEDS_ENGINEER_REVIEW
    elif value.needsReporterInfo:
        decision = Decision.NEEDS_REPORTER_INFO
    elif value.evidenceComplete and value.fixCandidate:
        decision = Decision.FIX_CANDIDATE
    else:
        decision = Decision.NEEDS_ENGINEER_REVIEW
    return BugAnalysisResult(decision, phase)
