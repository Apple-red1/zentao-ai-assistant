from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_serializer,
    field_validator,
    model_validator,
)


def deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(item) for item in value)
    return value


class FrozenModel(BaseModel):
    model_config = ConfigDict(
        frozen=True, populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    def model_post_init(self, __context: Any) -> None:
        for name in type(self).model_fields:
            object.__setattr__(self, name, deep_freeze(getattr(self, name)))


class RoutingData(FrozenModel):
    repositories: tuple[str, ...] = ()
    selected_repository: str | None = Field(None, alias="selectedRepository")
    layer: str | None = None
    matched_keywords: tuple[str, ...] = Field((), alias="matchedKeywords")
    confidence: Literal["high", "none"] = "none"
    evidence: tuple[str, ...] = ()


class CreatorAccount(FrozenModel):
    account: str


PresentationField = Literal["title", "priority", "status", "assignee"]


class BugSnapshot(FrozenModel):
    id: int | str
    status: str = "unknown"
    creator: CreatorAccount | None = None
    assignee: str | None = None
    version: str | None = None
    snapshot_version: str | None = Field(None, alias="snapshotVersion")
    snapshot_stable: bool = Field(False, alias="snapshotStable")
    title: str = "unknown"
    priority: str = "unknown"
    missing_presentation_fields: tuple[PresentationField, ...] = Field(
        (), alias="missingPresentationFields"
    )
    steps: str = ""
    routing: RoutingData | None = None
    raw: Mapping[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_snapshot_stability(self) -> Self:
        if self.snapshot_stable and not (self.version and self.snapshot_version):
            raise ValueError("stable snapshot requires version")
        if self.snapshot_stable and self.version != self.snapshot_version:
            raise ValueError("stable snapshot requires matching version")
        return self

    @field_validator("creator", mode="before")
    @classmethod
    def normalize_creator(cls, value: Any) -> Any:
        if value is None or isinstance(value, Mapping):
            return value
        return {"account": str(value)}


def missing_presentation_field_counts(
    items: Iterable[BugSnapshot],
) -> dict[PresentationField, int]:
    counts: dict[PresentationField, int] = {}
    for item in items:
        for field in item.missing_presentation_fields:
            counts[field] = counts.get(field, 0) + 1
    return counts


class BugHistoryEntry(FrozenModel):
    id: str | int | None = None
    action: str = ""
    actor: str | None = None
    idempotency_key: str | None = Field(None, alias="idempotencyKey")
    content_hash: str | None = Field(None, alias="contentHash")
    created: bool | None = None
    already_exists: bool | None = Field(None, alias="alreadyExists")
    raw: Mapping[str, Any] = Field(default_factory=dict)


class Coverage(FrozenModel):
    page: int = 1
    page_size: int = Field(20, alias="pageSize")
    total: int = 0
    pages: int | None = None
    returned: int = 0
    failed: int = 0
    complete: bool = True
    unstable_snapshots: int = Field(0, alias="unstableSnapshots")
    missing_presentation_fields: Mapping[PresentationField, int] = Field(
        default_factory=dict, alias="missingPresentationFields"
    )

    @field_serializer("missing_presentation_fields")
    def serialize_missing_presentation_fields(
        self, value: Mapping[PresentationField, int]
    ) -> dict[PresentationField, int]:
        return dict(value)

    @model_validator(mode="after")
    def reject_complete_failures(self) -> Self:
        if self.complete and self.failed:
            raise ValueError("failed results cannot be complete")
        return self


class ItemFailure(FrozenModel):
    bug_id: str | None = Field(None, alias="bugId")
    code: str
    field: str | None = None
    message: str


class ResolvedIdentity(FrozenModel):
    requested_identity: str = Field(alias="requestedIdentity")
    resolved_account: str | None = Field(None, alias="resolvedAccount")
    resolved_display_name: str | None = Field(None, alias="resolvedDisplayName")
    match_type: str | None = Field(None, alias="matchType")


class BugPage(FrozenModel):
    items: tuple[BugSnapshot, ...]
    coverage: Coverage
    item_failures: tuple[ItemFailure, ...] = Field((), alias="itemFailures")
    resolved_identity: ResolvedIdentity | None = Field(None, alias="resolvedIdentity")

    @model_validator(mode="after")
    def reject_complete_item_failures(self) -> Self:
        if self.coverage.complete and self.item_failures:
            raise ValueError("item failures require incomplete coverage")
        return self


class HistoryPage(FrozenModel):
    items: tuple[BugHistoryEntry, ...]
    coverage: Coverage


class BugStatistics(FrozenModel):
    values: Mapping[str, int] = Field(default_factory=dict)
    coverage: Coverage | None = None
    raw: Mapping[str, Any] = Field(default_factory=dict)


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
    login: str = "/api.php/v2/users/login"
    products: str = "/api.php/v2/products"
    product_bugs: str = Field(
        "/api.php/v2/products/{product_id}/bugs", alias="productBugs"
    )
    my_bugs: str = Field("/api/bugs/mine", alias="myBugs")
    user_bugs: str = Field("/api/bugs/user/{user}", alias="userBugs")
    global_bugs: str = Field("/api.php/v2/bugs", alias="globalBugs")
    bug_detail: str = Field("/api.php/v2/bugs/{bug_id}", alias="bugDetail")
    bug_history: str | None = Field(None, alias="bugHistory")
    statistics: str = "/api/bugs/statistics"
    add_comment: str = Field("/api/bugs/{bug_id}/comments", alias="addComment")
    update_steps: str = Field("/api/bugs/{bug_id}/steps", alias="updateSteps")
