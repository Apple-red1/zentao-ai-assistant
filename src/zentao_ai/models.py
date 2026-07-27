from __future__ import annotations

from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


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


class BugSummary(StrictModel):
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_assignee: dict[str, int] = Field(default_factory=dict)


class BugQueryResult(StrictModel):
    bugs: list[Bug]
    summary: BugSummary
    partial: bool = False
    warnings: list[str] = Field(default_factory=list)


class ActionResult(StrictModel):
    action: str
    bug_id: int
    before: Bug | None = None
    after: Bug | None = None
    message: str

