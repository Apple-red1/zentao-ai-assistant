from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zentao_ai.config.models import AppConfig
from zentao_ai.safety.actions import (
    ActionRequest,
    AuthorizationContext,
    AuthorizationRecord,
)
from zentao_ai.zentao.models import BugSnapshot

from .models import AnalysisPhase, AnalysisSignal
from .steps import ReproductionStep


@dataclass(frozen=True)
class WorkflowRequest:
    config: AppConfig
    snapshot: BugSnapshot
    phase: AnalysisPhase
    signal: AnalysisSignal
    scope_names: tuple[str, ...]
    authorization: AuthorizationContext
    actions: tuple[ActionRequest, ...]
    steps: tuple[ReproductionStep, ...]
    image_path: Path
    repair_bug_id: str


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be a mapping")
    return value


def _normalize(raw: Mapping[str, Any]) -> WorkflowRequest:
    config = AppConfig.model_validate(raw["config"])
    auth = _mapping(raw["authorization"], "authorization")
    context = dict(_mapping(auth["context"], "authorization.context"))
    records = tuple(
        AuthorizationRecord.model_validate(value) for value in auth["records"]
    )
    return WorkflowRequest(
        config=config,
        snapshot=BugSnapshot.model_validate(raw["snapshot"]),
        phase=AnalysisPhase(str(raw["phase"])),
        signal=AnalysisSignal(**dict(_mapping(raw["signal"], "signal"))),
        scope_names=tuple(config.personal.scopeNames),
        authorization=AuthorizationContext(
            **context, authorizationRecords=records
        ),
        actions=tuple(ActionRequest.model_validate(value) for value in raw["actions"]),
        steps=tuple(ReproductionStep(**value) for value in raw["steps"]),
        image_path=Path(str(raw["imagePath"])).expanduser().resolve(),
        repair_bug_id=str(raw["repairBugId"]),
    )


def normalize_cli_request(raw: Mapping[str, Any]) -> WorkflowRequest:
    """Normalize a parsed CLI request without making workflow decisions."""
    return _normalize(raw)


def normalize_codex_request(raw: str | Mapping[str, Any]) -> WorkflowRequest:
    """Normalize a Codex tool payload without making workflow decisions."""
    payload = json.loads(raw) if isinstance(raw, str) else raw
    return _normalize(_mapping(payload, "request"))
