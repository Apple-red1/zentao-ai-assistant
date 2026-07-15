from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ZentaoConfig(ConfigModel):
    baseUrl: str | None = None
    account: str | None = None
    password: str | None = None
    token: str | None = None
    cookie: str | None = None
    authorization: str | None = None


class PersonalConfig(ConfigModel):
    scopeNames: list[str] = Field(min_length=1)


class TeamConfig(ConfigModel):
    scopeNames: list[str] = Field(min_length=1)
    members: list[str] = Field(default_factory=list)


class LimitsConfig(ConfigModel):
    maxBugsPerRun: int = Field(default=50, gt=0, le=1000)


class RepositoryConfig(ConfigModel):
    repository: str
    path: str
    targetBranch: str
    testCommands: list[str]


class PermissionsConfig(ConfigModel):
    codeWriteEnabled: bool = False
    commentEnabled: bool = False
    stepUpdateEnabled: bool = False


class ReportingConfig(ConfigModel):
    outputDirectory: str = "reports"
    formats: list[str] = Field(default_factory=lambda: ["json"])


class ScheduleConfig(ConfigModel):
    timezone: str = "Asia/Shanghai"
    time: str = "08:00"
    includeWeekends: bool = True


class AppConfig(ConfigModel):
    configVersion: int = 1
    zentao: ZentaoConfig = Field(default_factory=ZentaoConfig)
    personal: PersonalConfig
    team: TeamConfig
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    repositories: dict[str, RepositoryConfig]
    permissions: PermissionsConfig = Field(default_factory=PermissionsConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)


class ValidationError(ConfigModel):
    field: str
    message: str


class ValidationResult(ConfigModel):
    valid: bool
    configVersion: int | None
    errors: list[ValidationError]
    redactedConfig: dict[str, Any] | None
