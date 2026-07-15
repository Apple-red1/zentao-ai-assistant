from __future__ import annotations

import itertools

import pytest

from zentao_ai.workflows.analysis import analyze_bug
from zentao_ai.workflows.models import AnalysisPhase, AnalysisSignal, Decision
from zentao_ai.zentao.models import BugSnapshot


def snapshot() -> BugSnapshot:
    return BugSnapshot(id=1, status="active", version="v1", snapshotVersion="v1")


@pytest.mark.parametrize(
    ("signal", "decision"),
    [
        (AnalysisSignal(), Decision.PROCEED_TO_EVIDENCE),
        (AnalysisSignal(needsReporterInfo=True), Decision.NEEDS_REPORTER_INFO),
        (AnalysisSignal(needsEngineerReview=True), Decision.NEEDS_ENGINEER_REVIEW),
        (AnalysisSignal(toolOrPermissionGap=True), Decision.TOOL_OR_PERMISSION_GAP),
    ],
)
def test_precheck_outcomes(signal: AnalysisSignal, decision: Decision) -> None:
    result = analyze_bug(snapshot(), (), AnalysisPhase.PRECHECK, signal=signal)
    assert result.decision is decision
    assert result.phase.value == "PRECHECK"


@pytest.mark.parametrize(
    "values", tuple(itertools.product((False, True), repeat=6))
)
def test_precheck_precedence_and_final_only_invariants(
    values: tuple[bool, ...],
) -> None:
    signal = AnalysisSignal(*values)
    result = analyze_bug(snapshot(), (), AnalysisPhase.PRECHECK, signal=signal)
    expected = (
        Decision.TOOL_OR_PERMISSION_GAP
        if signal.toolOrPermissionGap
        else Decision.NEEDS_ENGINEER_REVIEW
        if signal.needsEngineerReview
        else Decision.NEEDS_REPORTER_INFO
        if signal.needsReporterInfo
        else Decision.PROCEED_TO_EVIDENCE
    )
    assert result.decision is expected
    assert result.decision not in {
        Decision.FIX_CANDIDATE,
        Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION,
    }


@pytest.mark.parametrize(
    ("signal", "decision"),
    [
        (AnalysisSignal(toolOrPermissionGap=True), Decision.TOOL_OR_PERMISSION_GAP),
        (
            AnalysisSignal(patchRetained=True),
            Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION,
        ),
        (AnalysisSignal(needsEngineerReview=True), Decision.NEEDS_ENGINEER_REVIEW),
        (AnalysisSignal(needsReporterInfo=True), Decision.NEEDS_REPORTER_INFO),
        (
            AnalysisSignal(evidenceComplete=True, fixCandidate=True),
            Decision.FIX_CANDIDATE,
        ),
        (
            AnalysisSignal(fixCandidate=True),
            Decision.NEEDS_ENGINEER_REVIEW,
        ),
        (AnalysisSignal(), Decision.NEEDS_ENGINEER_REVIEW),
    ],
)
def test_final_outcomes(signal: AnalysisSignal, decision: Decision) -> None:
    result = analyze_bug(snapshot(), (), AnalysisPhase.FINAL_DECISION, signal=signal)
    assert result.decision is decision
    assert result.phase.value == "FINAL_DECISION"


@pytest.mark.parametrize(
    "values", tuple(itertools.product((False, True), repeat=6))
)
def test_final_precedence(values: tuple[bool, ...]) -> None:
    signal = AnalysisSignal(*values)
    result = analyze_bug(
        snapshot(), (), AnalysisPhase.FINAL_DECISION, signal=signal
    )
    expected = (
        Decision.TOOL_OR_PERMISSION_GAP
        if signal.toolOrPermissionGap
        else Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION
        if signal.patchRetained
        else Decision.NEEDS_ENGINEER_REVIEW
        if signal.needsEngineerReview
        else Decision.NEEDS_REPORTER_INFO
        if signal.needsReporterInfo
        else Decision.FIX_CANDIDATE
        if signal.evidenceComplete and signal.fixCandidate
        else Decision.NEEDS_ENGINEER_REVIEW
    )
    assert result.decision is expected
