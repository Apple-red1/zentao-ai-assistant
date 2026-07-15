from __future__ import annotations

import pytest

from zentao_ai.workflows.analysis import analyze_bug
from zentao_ai.workflows.models import AnalysisPhase, AnalysisSignal, Decision
from zentao_ai.zentao.models import BugSnapshot


def snapshot() -> BugSnapshot:
    return BugSnapshot(id=1, status="active", version="v1", snapshotVersion="v1")


@pytest.mark.parametrize(("phase", "signal", "decision"), [
    (AnalysisPhase.PRECHECK, AnalysisSignal(evidenceComplete=True, fixCandidate=True), Decision.PROCEED_TO_EVIDENCE),
    (AnalysisPhase.FINAL, AnalysisSignal(evidenceComplete=True, fixCandidate=True), Decision.FIX_CANDIDATE),
    (AnalysisPhase.FINAL, AnalysisSignal(needsReporterInfo=True), Decision.NEEDS_REPORTER_INFO),
    (AnalysisPhase.FINAL, AnalysisSignal(needsEngineerReview=True), Decision.NEEDS_ENGINEER_REVIEW),
    (AnalysisPhase.FINAL, AnalysisSignal(toolOrPermissionGap=True), Decision.TOOL_OR_PERMISSION_GAP),
])
def test_decision_contract(phase, signal, decision):
    assert analyze_bug(snapshot(), (), phase, signal=signal).decision is decision
