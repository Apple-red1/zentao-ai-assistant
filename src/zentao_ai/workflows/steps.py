from __future__ import annotations

import mimetypes
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from zentao_ai.safety.actions import ActionRequest, AuthorizationContext
from zentao_ai.safety.authorization import authorize
from zentao_ai.safety.images import CurrentTurnAuthorization, validate_user_image
from zentao_ai.zentao.models import StepUpdateResult

from .models import RunContext


@dataclass(frozen=True)
class ReproductionStep:
    action: str
    expected: str


def _complete_steps(steps: tuple[ReproductionStep, ...]) -> str:
    if not steps or any(
        not step.action.strip() or not step.expected.strip() for step in steps
    ):
        raise ValueError("ordered action and expected result are required")
    return json.dumps(
        [asdict(step) for step in steps], ensure_ascii=False, separators=(",", ":")
    )


def _permit(
    context: RunContext,
    action: Literal["update_steps", "update_steps_with_image"],
    bug_id: int | str,
    parameters: dict[str, object],
) -> None:
    if context.dryRun or context.readonly:
        raise PermissionError("write disabled")
    auth = AuthorizationContext(
        scheduled=context.scheduled,
        stepUpdateEnabled=context.config.permissions.stepUpdateEnabled,
        currentTurnId=context.currentTurnId,
        authorizationRecords=context.authorizationRecords,
    )
    decision = authorize(
        ActionRequest(action=action, bugId=str(bug_id), parameters=parameters), auth
    )
    if not decision.allowed:
        raise PermissionError(decision.reason)


def replace_steps(
    context: RunContext, bug_id: int | str, steps: tuple[ReproductionStep, ...]
) -> StepUpdateResult:
    rendered = _complete_steps(steps)
    params: dict[str, object] = {"steps": [asdict(step) for step in steps]}
    _permit(context, "update_steps", bug_id, params)
    return context.provider.update_bug_steps(bug_id, rendered, True)


def replace_steps_with_image(
    context: RunContext,
    bug_id: int | str,
    steps: tuple[ReproductionStep, ...],
    path: Path,
) -> StepUpdateResult:
    rendered = _complete_steps(steps)
    validation = validate_user_image(
        path,
        CurrentTurnAuthorization(
            paths=context.authorizedImagePaths,
            authorizationTurnId=context.currentTurnId,
            currentTurnId=context.currentTurnId,
        ),
    )
    if not validation.valid:
        raise PermissionError(",".join(validation.reasons))
    if validation.content is None or validation.filename is None:
        raise PermissionError("IMAGE_ARTIFACT_REQUIRED")
    params: dict[str, object] = {
        "steps": [asdict(step) for step in steps],
        "imageSha256": validation.sha256,
        "filename": validation.filename,
    }
    _permit(context, "update_steps_with_image", bug_id, params)
    return context.provider.update_bug_steps_with_image(
        bug_id,
        rendered,
        validation.content,
        validation.filename,
        mimetypes.guess_type(validation.filename)[0] or "application/octet-stream",
        True,
    )
