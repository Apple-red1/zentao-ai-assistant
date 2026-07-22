from __future__ import annotations

import itertools

import pytest

from zentao_ai.workflows.analysis import analyze_bug
from zentao_ai.workflows.models import AnalysisPhase, AnalysisSignal, Decision
from zentao_ai.zentao.models import BugSnapshot


def snapshot() -> BugSnapshot:
    return BugSnapshot(id=1, status="active", version="v1", snapshotVersion="v1")


def test_login_page_style_only_bug_can_enter_evidence_without_manual_review() -> None:
    bug = BugSnapshot(
        id=3397,
        status="active",
        version="v1",
        snapshotVersion="s1",
        title="【站点后台】登录按钮背景色改为白色，文字改为黑色",
        steps="[步骤]登录页按钮演示\n[结果]登录按钮黑底白字\n[期望]登录按钮背景色改为白色，文字改为黑色",
        routing={
            "repositories": ["ce-site-backend"],
            "selectedRepository": "ce-site-backend",
            "layer": "frontend",
            "confidence": 1.0,
        },
    )
    result = analyze_bug(bug, (), AnalysisPhase.PRECHECK)
    assert result.decision is Decision.PROCEED_TO_EVIDENCE


def test_login_security_terms_still_require_engineer_review() -> None:
    bug = BugSnapshot(
        id=9,
        status="active",
        version="v1",
        snapshotVersion="s1",
        title="【站点后台】登录接口鉴权失败",
        steps="[步骤]登录\n[结果]token 权限校验异常\n[期望]修复认证逻辑",
        routing={
            "repositories": ["cms-center"],
            "selectedRepository": "cms-center",
            "layer": "backend",
            "confidence": 1.0,
        },
    )
    result = analyze_bug(bug, (), AnalysisPhase.PRECHECK)
    assert result.decision is Decision.NEEDS_ENGINEER_REVIEW


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
