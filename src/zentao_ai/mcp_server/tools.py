from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from collections.abc import Mapping
from typing import Any, cast

from pydantic import BaseModel

from zentao_ai.cli.runtime import AppRuntime
from zentao_ai.safety.actions import ActionName, ActionRequest
from zentao_ai.workflows.adapters import WorkflowRequest, normalize_codex_request
from zentao_ai.workflows.comments import _write_comment
from zentao_ai.workflows.steps import (
    ReproductionStep,
    replace_steps,
    replace_steps_with_image,
)
from zentao_ai.zentao.models import BugPage, Coverage
from zentao_ai.zentao.query_filters import filter_assignee_bugs

from .schemas import (
    INPUT_MODELS,
    AddCommentInput,
    QueryBugDetailInput,
    QueryBugHistoryInput,
    QueryMyBugsInput,
    QueryUserBugsInput,
    UpdateStepsInput,
    UpdateStepsWithImageInput,
)

TOOL_NAMES = (
    "query_my_bugs",
    "query_user_bugs",
    "query_bug_detail",
    "query_bug_history",
    "bug_statistics",
    "add_bug_comment",
    "update_bug_steps",
    "update_bug_steps_with_image",
)


def _json(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    if isinstance(value, BaseModel):
        return _json(value.model_dump(mode="python", by_alias=True, warnings=False))
    if hasattr(value, "__dataclass_fields__"):
        return asdict(cast(Any, value))
    return value


class ZentaoTools:
    def __init__(self, runtime: AppRuntime) -> None:
        self.runtime = runtime

    @staticmethod
    def schemas() -> dict[str, dict[str, Any]]:
        return {name: INPUT_MODELS[name].model_json_schema() for name in TOOL_NAMES}

    def _normalized(self, value: AddCommentInput | UpdateStepsInput) -> WorkflowRequest:
        snapshot = self.runtime.provider.query_bug_detail(value.bugId)
        authorization = value.authorization
        record = {
            "turnId": authorization.turnId,
            "source": authorization.source,
            "action": authorization.action,
            "bugId": str(authorization.bugId),
            "parameters": authorization.parameters,
        }
        return normalize_codex_request(
            {
                "config": _json(self.runtime.config),
                "snapshot": _json(snapshot),
                "phase": "PRECHECK",
                "signal": {},
                "authorization": {
                    "context": {
                        "scheduled": value.scheduled or value.nonInteractive,
                        "commentEnabled": self.runtime.config.permissions.commentEnabled,
                        "stepUpdateEnabled": self.runtime.config.permissions.stepUpdateEnabled,
                        "snapshotStable": getattr(value, "snapshotStable", False),
                        "historyChecked": getattr(value, "historyChecked", False),
                        "cooldownPassed": getattr(value, "cooldownPassed", False),
                        "idempotencyPassed": getattr(value, "idempotencyPassed", False),
                        "currentTurnId": value.currentTurnId,
                    },
                    "records": [record],
                },
                "actions": [
                    ActionRequest(
                        action=cast(ActionName, authorization.action),
                        bugId=str(authorization.bugId),
                        parameters=authorization.parameters,
                        source=authorization.source,
                    ).model_dump(mode="json")
                ],
                "steps": []
                if isinstance(value, AddCommentInput)
                else [item.model_dump() for item in value.steps],
                "imagePath": value.imagePath
                if isinstance(value, UpdateStepsWithImageInput)
                else str(Path.cwd()),
                "repairBugId": str(value.bugId),
            }
        )

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        model = INPUT_MODELS.get(name)
        if model is None:
            raise ValueError("unknown tool")
        value = model.model_validate(arguments)
        provider = self.runtime.provider
        data: object
        if name == "query_my_bugs":
            assert isinstance(value, QueryMyBugsInput)
            account = self.runtime.config.zentao.account
            if account is None or not account.strip():
                raise RuntimeError("configuration error")
            source = provider.query_user_bugs(
                account.strip(),
                scope_names=(),
                page=value.page,
                page_size=value.pageSize,
                browse_type="assigntome",
            )
            items = filter_assignee_bugs(
                source.items, title_tag=value.titleTag, status=value.status
            )
            coverage = source.coverage
            complete = coverage.complete and (
                coverage.page == 1
                and coverage.pages is not None
                and coverage.pages == (0 if not source.items else 1)
                and coverage.total == len(source.items)
            )
            coverage = Coverage(
                page=value.page,
                pageSize=value.pageSize,
                total=len(items) if complete else -1,
                pages=(0 if not items else 1) if complete else None,
                returned=len(items),
                failed=coverage.failed,
                complete=complete,
            )
            data = BugPage(
                items=items,
                coverage=coverage,
                itemFailures=source.item_failures,
                resolvedIdentity=source.resolved_identity,
            )
        elif name == "query_user_bugs":
            assert isinstance(value, QueryUserBugsInput)
            data = provider.query_user_bugs(
                value.user,
                scope_names=tuple(self.runtime.config.team.scopeNames),
                page=value.page,
                page_size=value.pageSize,
            )
        elif name == "query_bug_detail":
            assert isinstance(value, QueryBugDetailInput)
            data = provider.query_bug_detail(value.bugId)
        elif name == "query_bug_history":
            assert isinstance(value, QueryBugHistoryInput)
            data = provider.query_bug_history(
                value.bugId, page=value.page, page_size=value.pageSize
            )
        elif name == "bug_statistics":
            data = provider.bug_statistics()
        elif name == "add_bug_comment":
            assert isinstance(value, AddCommentInput)
            normalized = self._normalized(value)
            context = self.runtime.context(
                scheduled=normalized.authorization.scheduled,
                currentTurnId=normalized.authorization.currentTurnId,
                authorizationRecords=normalized.authorization.authorizationRecords,
                snapshotStable=normalized.authorization.snapshotStable,
                historyChecked=normalized.authorization.historyChecked,
                cooldownPassed=normalized.authorization.cooldownPassed,
                idempotencyPassed=normalized.authorization.idempotencyPassed,
            )
            data = _write_comment(
                context,
                normalized.snapshot,
                value.comment,
                idempotency_key=value.idempotencyKey,
            )
        else:
            assert isinstance(value, UpdateStepsInput)
            normalized = self._normalized(value)
            context = self.runtime.context(
                scheduled=normalized.authorization.scheduled,
                currentTurnId=normalized.authorization.currentTurnId,
                authorizationRecords=normalized.authorization.authorizationRecords,
                authorizedImagePaths=tuple(
                    Path(item).resolve(strict=False)
                    for item in value.authorization.authorizedImagePaths
                ),
            )
            steps = tuple(
                ReproductionStep(item.action, item.expected) for item in value.steps
            )
            data = (
                replace_steps_with_image(
                    context, value.bugId, steps, normalized.image_path
                )
                if isinstance(value, UpdateStepsWithImageInput)
                else replace_steps(context, value.bugId, steps)
            )
        return {"version": "v1", "data": _json(data)}
