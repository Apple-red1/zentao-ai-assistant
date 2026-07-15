from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import cast

from zentao_ai.safety.actions import ActionRequest, AuthorizationContext
from zentao_ai.safety.authorization import authorize
from zentao_ai.safety.images import CurrentTurnAuthorization, validate_user_image
from zentao_ai.zentao.models import StepUpdateResult

from .models import RunContext


def _permit(context: RunContext, action: str, bug_id: int | str, parameters: dict[str, object]) -> None:
    if context.dryRun or context.readonly:
        raise PermissionError("write disabled")
    auth = AuthorizationContext(scheduled=context.scheduled, stepUpdateEnabled=context.config.permissions.stepUpdateEnabled, currentTurnId=context.currentTurnId, authorizationRecords=context.authorizationRecords)
    decision = authorize(ActionRequest(action=action, bugId=str(bug_id), parameters=parameters), auth)  # type: ignore[arg-type]
    if not decision.allowed:
        raise PermissionError(decision.reason)


def replace_steps(context: RunContext, bug_id: int | str, steps: str) -> StepUpdateResult:
    if not steps.strip():
        raise ValueError("complete replacement steps required")
    params: dict[str, object] = {"steps": steps}
    _permit(context, "update_steps", bug_id, params)
    return cast(StepUpdateResult, context.provider.update_bug_steps(bug_id, steps, True))


def replace_steps_with_image(context: RunContext, bug_id: int | str, steps: str, path: Path) -> StepUpdateResult:
    params: dict[str, object] = {"steps": steps, "imagePath": str(path)}
    _permit(context, "update_steps_with_image", bug_id, params)
    validation = validate_user_image(path, CurrentTurnAuthorization(paths=context.authorizedImagePaths, authorizationTurnId=context.currentTurnId, currentTurnId=context.currentTurnId))
    if not validation.valid:
        raise PermissionError(",".join(validation.reasons))
    data = path.read_bytes()
    return cast(
        StepUpdateResult,
        context.provider.update_bug_steps_with_image(
            bug_id,
            steps,
            data,
            path.name,
            mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            True,
        ),
    )
