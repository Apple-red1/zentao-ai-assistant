from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from zentao_ai.config.models import AppConfig
from zentao_ai.safety.actions import (
    ActionRequest,
    AuthorizationContext,
    AuthorizationRecord,
)
from zentao_ai.safety.authorization import authorize
from zentao_ai.workflows.analysis import analyze_bug
from zentao_ai.workflows.models import AnalysisPhase, AnalysisSignal, Decision
from zentao_ai.workflows.steps import ReproductionStep
from zentao_ai.zentao.models import BugSnapshot


@dataclass(frozen=True)
class SharedInputs:
    snapshot: BugSnapshot
    phase: AnalysisPhase
    signal: AnalysisSignal
    scope_names: tuple[str, ...]
    authorization: AuthorizationContext
    actions: tuple[ActionRequest, ...]
    steps: tuple[ReproductionStep, ...]
    image_path: Path
    repair_bug_id: str


def _normalize(payload: dict[str, object]) -> SharedInputs:
    config = AppConfig.model_validate(payload["config"])
    auth = payload["authorization"]
    assert isinstance(auth, dict)
    records = tuple(AuthorizationRecord.model_validate(v) for v in auth["records"])
    return SharedInputs(
        snapshot=BugSnapshot.model_validate(payload["snapshot"]),
        phase=AnalysisPhase(str(payload["phase"])),
        signal=AnalysisSignal(**dict(payload["signal"])),
        scope_names=tuple(config.personal.scopeNames),
        authorization=AuthorizationContext(
            **dict(auth["context"]), authorizationRecords=records
        ),
        actions=tuple(ActionRequest.model_validate(v) for v in payload["actions"]),
        steps=tuple(ReproductionStep(**v) for v in payload["steps"]),
        image_path=Path(str(payload["imagePath"])).resolve(),
        repair_bug_id=str(payload["repairBugId"]),
    )


def cli_adapter(argv_payload: dict[str, object]) -> SharedInputs:
    """Synthetic CLI boundary: parse strings, then delegate normalization."""
    return _normalize(json.loads(json.dumps(argv_payload)))


def codex_adapter(tool_payload_json: str) -> SharedInputs:
    """Synthetic Codex boundary: decode tool JSON, then delegate normalization."""
    return _normalize(json.loads(tool_payload_json))


def _payload(
    tmp_path: Path, phase: AnalysisPhase, signal: AnalysisSignal
) -> dict[str, object]:
    steps = [{"action": "Open the synthetic page", "expected": "Page is visible"}]
    comment = "Please provide the failing request"
    records = [
        {
            "turnId": "turn-1",
            "source": "user",
            "action": "comment",
            "bugId": "7",
            "parameters": {"comment": comment},
        },
        {
            "turnId": "turn-1",
            "source": "user",
            "action": "update_steps",
            "bugId": "7",
            "parameters": {"steps": steps},
        },
        {
            "turnId": "turn-1",
            "source": "user",
            "action": "update_steps_with_image",
            "bugId": "7",
            "parameters": {
                "steps": steps,
                "image": "proof.png",
            },
        },
    ]
    return {
        "snapshot": {
            "id": 7,
            "status": "active",
            "version": "v1",
            "snapshotVersion": "v1",
        },
        "phase": phase.value,
        "signal": signal.__dict__,
        "config": {
            "personal": {"scopeNames": ["Example Site"]},
            "team": {"scopeNames": ["Example Team"]},
            "repositories": {},
            "permissions": {"commentEnabled": True, "stepUpdateEnabled": True},
        },
        "authorization": {
            "context": {
                "commentEnabled": True,
                "stepUpdateEnabled": True,
                "snapshotStable": True,
                "historyChecked": True,
                "cooldownPassed": True,
                "idempotencyPassed": True,
                "currentTurnId": "turn-1",
            },
            "records": records,
        },
        "actions": [
            {
                "action": "comment",
                "bugId": "7",
                "parameters": {"comment": comment},
            },
            {
                "action": "update_steps",
                "bugId": "7",
                "parameters": {"steps": steps},
            },
            {
                "action": "update_steps_with_image",
                "bugId": "7",
                "parameters": {"steps": steps, "image": "proof.png"},
            },
        ],
        "steps": steps,
        "imagePath": str(tmp_path / "proof.png"),
        "repairBugId": 7,
    }


CASES = [
    (AnalysisPhase.PRECHECK, AnalysisSignal(), Decision.PROCEED_TO_EVIDENCE),
    (
        AnalysisPhase.PRECHECK,
        AnalysisSignal(needsReporterInfo=True),
        Decision.NEEDS_REPORTER_INFO,
    ),
    (
        AnalysisPhase.PRECHECK,
        AnalysisSignal(needsEngineerReview=True),
        Decision.NEEDS_ENGINEER_REVIEW,
    ),
    (
        AnalysisPhase.PRECHECK,
        AnalysisSignal(toolOrPermissionGap=True),
        Decision.TOOL_OR_PERMISSION_GAP,
    ),
    (
        AnalysisPhase.FINAL_DECISION,
        AnalysisSignal(needsReporterInfo=True),
        Decision.NEEDS_REPORTER_INFO,
    ),
    (
        AnalysisPhase.FINAL_DECISION,
        AnalysisSignal(needsEngineerReview=True),
        Decision.NEEDS_ENGINEER_REVIEW,
    ),
    (
        AnalysisPhase.FINAL_DECISION,
        AnalysisSignal(toolOrPermissionGap=True),
        Decision.TOOL_OR_PERMISSION_GAP,
    ),
    (
        AnalysisPhase.FINAL_DECISION,
        AnalysisSignal(patchRetained=True),
        Decision.PATCH_RETAINED_FOR_HUMAN_VALIDATION,
    ),
    (
        AnalysisPhase.FINAL_DECISION,
        AnalysisSignal(evidenceComplete=True, fixCandidate=True),
        Decision.FIX_CANDIDATE,
    ),
    (
        AnalysisPhase.FINAL_DECISION,
        AnalysisSignal(fixCandidate=True),
        Decision.NEEDS_ENGINEER_REVIEW,
    ),
    (AnalysisPhase.FINAL_DECISION, AnalysisSignal(), Decision.NEEDS_ENGINEER_REVIEW),
]


@pytest.mark.parametrize(("phase", "signal", "expected"), CASES)
def test_cli_and_codex_equivalent_inputs_use_shared_decisions_and_safety(
    tmp_path: Path,
    phase: AnalysisPhase,
    signal: AnalysisSignal,
    expected: Decision,
) -> None:
    payload = _payload(tmp_path, phase, signal)
    cli = cli_adapter(payload)
    codex = codex_adapter(json.dumps(payload))

    assert cli == codex
    cli_result = analyze_bug(cli.snapshot, (), cli.phase, signal=cli.signal)
    codex_result = analyze_bug(codex.snapshot, (), codex.phase, signal=codex.signal)
    assert cli_result == codex_result
    assert cli_result.decision is expected

    cli_recording = tuple(
        (request.action, authorize(request, cli.authorization))
        for request in cli.actions
    )
    codex_recording = tuple(
        (request.action, authorize(request, codex.authorization))
        for request in codex.actions
    )
    assert cli_recording == codex_recording
    assert all(decision.allowed for _, decision in cli_recording)


def test_adapters_cannot_bypass_shared_configuration_or_authorization(
    tmp_path: Path,
) -> None:
    payload = _payload(tmp_path, AnalysisPhase.PRECHECK, AnalysisSignal())
    payload["config"]["permissions"]["stepUpdateEnabled"] = False
    payload["authorization"]["context"]["stepUpdateEnabled"] = False
    cli = cli_adapter(payload)
    codex = codex_adapter(json.dumps(payload))

    for left, right in zip(cli.actions, codex.actions, strict=True):
        assert authorize(left, cli.authorization) == authorize(
            right, codex.authorization
        )
    assert not authorize(cli.actions[1], cli.authorization).allowed
