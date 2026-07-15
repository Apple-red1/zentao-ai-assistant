from typing import Any, Literal
from pydantic import BaseModel, Field


class ActionRequest(BaseModel):
    action: str
    bugId: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    source: Literal["user", "bug", "history", "web"] = "user"


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
    explicitActions: tuple[str, ...] = ()
    bugId: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class AuthorizationDecision(BaseModel):
    allowed: bool
    reason: str
