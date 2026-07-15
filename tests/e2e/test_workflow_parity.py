from __future__ import annotations

import json
import hashlib
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from zentao_ai.safety.authorization import authorize
from zentao_ai.state.models import OutboxRecord, OutboxStatus
from zentao_ai.workflows.analysis import analyze_bug
from zentao_ai.workflows.adapters import normalize_cli_request, normalize_codex_request
from zentao_ai.workflows.comments import (
    canonical_resolution_comment,
    write_resolution_comment,
)
from zentao_ai.workflows.models import AnalysisPhase, AnalysisSignal, Decision
from zentao_ai.workflows.models import RunContext
from zentao_ai.workflows.personal import run_personal
from zentao_ai.workflows.repair import repair_bug
from zentao_ai.workflows.steps import replace_steps, replace_steps_with_image
from zentao_ai.workflows.team_report import run_team_report
from zentao_ai.zentao.models import (
    BugPage,
    BugSnapshot,
    CommentWriteResult,
    Coverage,
    HistoryPage,
    StepUpdateResult,
)


def _payload(
    tmp_path: Path, phase: AnalysisPhase, signal: AnalysisSignal
) -> dict[str, object]:
    image_path = tmp_path / "proof.png"
    image = b"\x89PNG\r\n\x1a\nsynthetic"
    image_path.write_bytes(image)
    steps = [{"action": "Open the synthetic page", "expected": "Page is visible"}]
    summary = "Please provide the failing request"
    comment = canonical_resolution_comment(summary)
    image_parameters = {
        "steps": steps,
        "imageSha256": hashlib.sha256(image).hexdigest(),
        "filename": "proof.png",
    }
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
            "parameters": image_parameters,
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
            "permissions": {
                "codeWriteEnabled": True,
                "commentEnabled": True,
                "stepUpdateEnabled": True,
            },
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
                "parameters": image_parameters,
            },
        ],
        "steps": steps,
        "imagePath": str(image_path),
        "repairBugId": 7,
        "commentSummary": summary,
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
    cli = normalize_cli_request(payload)
    codex = normalize_codex_request(json.dumps(payload))

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
    cli = normalize_cli_request(payload)
    codex = normalize_codex_request(json.dumps(payload))

    for left, right in zip(cli.actions, codex.actions, strict=True):
        assert authorize(left, cli.authorization) == authorize(
            right, codex.authorization
        )
    assert not authorize(cli.actions[1], cli.authorization).allowed


class RecordingProvider:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def _snapshot(self, bug_id: object) -> BugSnapshot:
        return BugSnapshot(
            id=bug_id,
            status="active",
            version="v1",
            snapshotVersion="v1",
            creator={"account": "reporter"},
        )

    def query_my_bugs(self, *, scope_names, page=1, page_size=20):
        self.calls.append(("mine", tuple(scope_names)))
        return BugPage(items=(self._snapshot(7),), coverage=Coverage(total=1))

    def query_user_bugs(self, user, *, scope_names, page=1, page_size=20):
        self.calls.append(("team", user, tuple(scope_names)))
        return BugPage(items=(self._snapshot(7),), coverage=Coverage(total=1))

    def query_bug_detail(self, bug_id):
        self.calls.append(("detail", str(bug_id)))
        return self._snapshot(bug_id)

    def query_bug_history(self, bug_id, *, page=1, page_size=20):
        self.calls.append(("history", str(bug_id)))
        return HistoryPage(items=(), coverage=Coverage(total=0))

    def add_bug_comment(self, bug_id, comment, confirm, idempotency_key):
        self.calls.append(("comment", str(bug_id), comment, confirm))
        return CommentWriteResult(
            created=True, alreadyExists=False, status="CREATED"
        )

    def reconcile_comment(self, *args, **kwargs):
        raise AssertionError("unexpected reconciliation")

    def update_bug_steps(self, bug_id, steps, confirm=True):
        self.calls.append(("steps", str(bug_id), steps, confirm))
        return StepUpdateResult(updated=True, bugId=bug_id)

    def update_bug_steps_with_image(
        self, bug_id, steps, image, filename, content_type, confirm=True
    ):
        self.calls.append(
            ("image", str(bug_id), steps, image, filename, content_type, confirm)
        )
        return StepUpdateResult(updated=True, bugId=bug_id)


class RecordingLedger:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def acquire_lease(self, business_date, kind, owner, ttl_seconds):
        self.calls.append(("lease", kind))
        return type("Lease", (), {"acquired": True, "lease_id": kind})()

    def release_lease(self, lease_id, status):
        self.calls.append(("release", lease_id, status))

    def put_checkpoint(self, business_date, kind, payload):
        self.calls.append(("checkpoint", kind, payload["scopeNames"]))

    def put_outbox(self, record):
        self.calls.append(("outbox", record.run_kind))
        return replace(record, status=OutboxStatus.PENDING)

    def mark_outbox_result(self, key, status, external_id):
        self.calls.append(("outbox_result", status))
        return OutboxRecord(key, "comment", {}, status)


def _exercise(request, summary: str):
    provider = RecordingProvider()
    ledger = RecordingLedger()
    context = RunContext(
        request.config,
        provider,
        ledger,
        lambda: datetime(2026, 7, 15, 9),
        "owner",
        analysis=lambda *_: request.signal,
        currentTurnId="turn-1",
        authorizationRecords=request.authorization.authorizationRecords,
        authorizedImagePaths=(request.image_path,),
        snapshotStable=True,
        historyChecked=True,
        cooldownPassed=True,
        idempotencyPassed=True,
    )
    personal = run_personal(context)
    team = run_team_report(context)
    comment = write_resolution_comment(context, request.snapshot, summary)
    steps = replace_steps(context, request.repair_bug_id, request.steps)
    image = replace_steps_with_image(
        context, request.repair_bug_id, request.steps, request.image_path
    )
    repair = repair_bug(context, request.repair_bug_id)
    return (personal, team, comment, steps, image, repair), (
        tuple(provider.calls),
        tuple(ledger.calls),
    )


def test_production_adapters_drive_identical_public_workflows_and_side_effects(
    tmp_path: Path,
) -> None:
    signal = AnalysisSignal(evidenceComplete=True, fixCandidate=True)
    payload = _payload(tmp_path, AnalysisPhase.FINAL_DECISION, signal)
    cli = normalize_cli_request(payload)
    codex = normalize_codex_request(json.dumps(payload))

    cli_results, cli_recording = _exercise(cli, str(payload["commentSummary"]))
    codex_results, codex_recording = _exercise(
        codex, str(payload["commentSummary"])
    )

    assert cli_results == codex_results
    assert cli_recording == codex_recording
    assert cli_results[0].scopeNames == cli.scope_names
    assert cli_results[1].scopeNames == tuple(cli.config.team.scopeNames)
    assert cli_results[-1].bugId == cli.repair_bug_id
    assert ("detail", cli.repair_bug_id) in cli_recording[0]
    assert any(call[0] == "steps" for call in cli_recording[0])
    assert any(call[0] == "image" for call in cli_recording[0])
