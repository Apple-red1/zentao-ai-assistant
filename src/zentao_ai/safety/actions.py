from typing import Any, Literal, TypeAlias
from pydantic import BaseModel, Field


ActionName: TypeAlias = Literal[
    "query", "analyze", "report", "comment", "update_steps", "update_steps_with_image",
    "update_status", "assign_bug", "activate_bug", "resolve_bug", "close_bug", "create_bug",
    "convert_bug_to_task", "write_code", "commit", "push", "merge", "deploy", "reset",
    "checkout", "delete_bug", "remove_bug", "purge_bug", "destroy_bug",
]


class ActionRequest(BaseModel):
    action: ActionName
    bugId: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    source: Literal["user", "bug", "history", "web"] = "user"


class AuthorizationRecord(BaseModel):
    turnId: str
    source: Literal["user", "bug", "history", "web"]
    action: ActionName
    bugId: str
    parameters: dict[str, Any]


class AuthorizationContext(BaseModel):
    scheduled: bool = False
    commentEnabled: bool = False
    codeWriteEnabled: bool = False
    snapshotStable: bool = False
    historyChecked: bool = False
    cooldownPassed: bool = False
    idempotencyPassed: bool = False
    routingUnique: bool = False
    repositoryGuardPassed: bool = False
    currentTurnId: str | None = None
    authorizationRecords: tuple[AuthorizationRecord, ...] = ()
    stepUpdateEnabled: bool = False
    bugId: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class AuthorizationDecision(BaseModel):
    allowed: bool
    reason: str
