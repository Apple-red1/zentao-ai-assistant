from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TeamMember(StrictModel):
    name: str = Field(min_length=1)
    account: str = Field(min_length=1)


class ZentaoSettings(StrictModel):
    base_url: AnyHttpUrl
    api_version: Literal["v2"] = "v2"
    account: str = Field(min_length=1)


class QueryDefaults(StrictModel):
    default_status: Literal["unresolved", "active", "resolved", "closed", "all"] = (
        "unresolved"
    )
    page_size: int = Field(default=100, ge=1, le=1000)
    max_results: int = Field(default=500, ge=1, le=5000)


class WriteSettings(StrictModel):
    enabled: bool = True


class TeamSettings(StrictModel):
    members: list[TeamMember] = Field(default_factory=list)


class Settings(StrictModel):
    version: Literal[1]
    zentao: ZentaoSettings
    team: TeamSettings = Field(default_factory=TeamSettings)
    query: QueryDefaults = Field(default_factory=QueryDefaults)
    writes: WriteSettings = Field(default_factory=WriteSettings)


class User(StrictModel):
    id: int | None = None
    account: str
    real_name: str = ""
    deleted: bool = False


class UserRef(StrictModel):
    id: str
    account: str
    real_name: str = ""
    kind: Literal["inside", "outside"]


class TeamValidationFailure(StrictModel):
    name: str
    account: str
    code: str
    reason: str


class TeamValidationResult(StrictModel):
    resolved: list[UserRef] = Field(default_factory=list)
    failures: list[TeamValidationFailure] = Field(default_factory=list)


class Bug(StrictModel):
    id: int
    title: str
    status: str = ""
    severity: int | str | None = None
    priority: int | str | None = None
    assigned_to: str = ""
    opened_by: str = ""
    product: int | str | None = None
    opened_build: list[str] | str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class BugFilters(StrictModel):
    status: Literal["unresolved", "active", "resolved", "closed", "all"] = "unresolved"
    assigned_to: list[str] = Field(default_factory=list)
    opened_by: list[str] = Field(default_factory=list)
    product_id: int | None = Field(default=None, gt=0)
    project_id: int | None = Field(default=None, gt=0)
    execution_id: int | None = Field(default=None, gt=0)
    priority: list[int | str] = Field(default_factory=list)
    severity: list[int | str] = Field(default_factory=list)
    bug_type: list[str] = Field(default_factory=list)
    keyword: str | None = None
    opened_after: datetime | None = None
    opened_before: datetime | None = None
    edited_after: datetime | None = None
    edited_before: datetime | None = None
    order_by: Literal[
        "id",
        "-id",
        "priority",
        "-priority",
        "severity",
        "-severity",
        "opened_at",
        "-opened_at",
        "edited_at",
        "-edited_at",
    ] = "id"
    max_results: int | None = Field(default=None, ge=1, le=5000)

    @field_validator("opened_after", "opened_before", "edited_after", "edited_before")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("date filters must include a timezone")
        return value


class BugRecord(StrictModel):
    id: int
    title: str
    status: str = ""
    severity: int | str | None = None
    priority: int | str | None = None
    assigned_to: str = ""
    opened_by: str = ""
    product_id: int | None = None
    project_id: int | None = None
    execution_id: int | None = None
    bug_type: str = ""
    opened_at: datetime | None = None
    edited_at: datetime | None = None
    opened_build_ids: list[str] = Field(default_factory=list)
    steps: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class BugSummary(StrictModel):
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    by_assignee: dict[str, int] = Field(default_factory=dict)


class BugQueryResult(StrictModel):
    bugs: list[BugRecord]
    summary: BugSummary
    truncated: bool = False
    partial_failures: list[dict[str, str]] = Field(default_factory=list)


class ActionResult(StrictModel):
    action: str
    bug_id: int
    before: Bug | None = None
    after: Bug | None = None
    message: str
