from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")


class RoutingData(FrozenModel):
    repositories: tuple[str, ...] = ()
    selected_repository: str | None = Field(None, alias="selectedRepository")
    confidence: float | None = None


class BugSnapshot(FrozenModel):
    id: int | str
    status: str
    creator: str | None = None
    assignee: str | None = None
    version: str
    snapshot_version: str = Field(alias="snapshotVersion")
    title: str = ""
    steps: str = ""
    routing: RoutingData | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class BugHistoryEntry(FrozenModel):
    id: str | int | None = None
    action: str = ""
    actor: str | None = None
    idempotency_key: str | None = Field(None, alias="idempotencyKey")
    content_hash: str | None = Field(None, alias="contentHash")
    created: bool | None = None
    already_exists: bool | None = Field(None, alias="alreadyExists")
    raw: dict[str, Any] = Field(default_factory=dict)


class Coverage(FrozenModel):
    page: int = 1
    page_size: int = Field(20, alias="pageSize")
    total: int = 0
    pages: int | None = None


class BugPage(FrozenModel):
    items: tuple[BugSnapshot, ...]
    coverage: Coverage


class HistoryPage(FrozenModel):
    items: tuple[BugHistoryEntry, ...]
    coverage: Coverage


class BugStatistics(FrozenModel):
    values: dict[str, int] = Field(default_factory=dict)
    coverage: Coverage | None = None


class CommentWriteResult(FrozenModel):
    created: bool
    already_exists: bool = Field(alias="alreadyExists")
    comment_id: str | int | None = Field(None, alias="commentId")
    status: Literal["CREATED", "ALREADY_EXISTS", "UNKNOWN"]


class StepUpdateResult(FrozenModel):
    updated: bool
    bug_id: int | str = Field(alias="bugId")
    version: str | None = None
    status: str = "UPDATED"


class ZentaoAuth(FrozenModel):
    username: str | None = None
    password: SecretStr | None = None
    api_token: SecretStr | None = Field(None, alias="apiToken")
    web_cookie: SecretStr | None = Field(None, alias="webCookie")


class ZentaoEndpoints(FrozenModel):
    my_bugs: str = Field("/api/bugs/mine", alias="myBugs")
    user_bugs: str = Field("/api/bugs/user/{user}", alias="userBugs")
    bug_detail: str = Field("/api/bugs/{bug_id}", alias="bugDetail")
    bug_history: str = Field("/api/bugs/{bug_id}/history", alias="bugHistory")
    statistics: str = "/api/bugs/statistics"
    add_comment: str = Field("/api/bugs/{bug_id}/comments", alias="addComment")
    update_steps: str = Field("/api/bugs/{bug_id}/steps", alias="updateSteps")
