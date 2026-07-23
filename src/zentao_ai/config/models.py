from __future__ import annotations

import unicodedata
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator, model_validator


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ZentaoConfig(ConfigModel):
    baseUrl: str | None = None
    account: str | None = None
    password: str | None = None
    token: str | None = None
    cookie: str | None = None
    authorization: str | None = None
    secret: str | None = None


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


class TitleRoutingConfig(ConfigModel):
    marker: str = Field(min_length=1)
    frontendRepository: str = Field(min_length=1)
    backendRepository: str = Field(min_length=1)
    frontendKeywords: list[str] = Field(default_factory=list)
    backendKeywords: list[str] = Field(default_factory=list)

    @field_validator("marker", "frontendRepository", "backendRepository")
    @classmethod
    def trim_nonempty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed

    @field_validator("frontendKeywords", "backendKeywords")
    @classmethod
    def trim_keywords(cls, values: list[str]) -> list[str]:
        trimmed = [value.strip() for value in values]
        if any(not value for value in trimmed):
            raise ValueError("keywords must not be blank")
        return trimmed


class PermissionsConfig(ConfigModel):
    codeWriteEnabled: StrictBool = False
    commentEnabled: StrictBool = False
    stepUpdateEnabled: StrictBool = False


class ReportingConfig(ConfigModel):
    outputDirectory: str = "reports"
    formats: list[str] = Field(default_factory=lambda: ["json"])


class ScheduleConfig(ConfigModel):
    timezone: str = "Asia/Shanghai"
    time: str = "08:00"
    includeWeekends: bool = True


class AppConfig(ConfigModel):
    configVersion: StrictInt = 1
    zentao: ZentaoConfig = Field(default_factory=ZentaoConfig)
    personal: PersonalConfig
    team: TeamConfig
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    repositories: dict[str, RepositoryConfig]
    titleRouting: list[TitleRoutingConfig] = Field(default_factory=list)
    permissions: PermissionsConfig = Field(default_factory=PermissionsConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)

    @field_validator("configVersion")
    @classmethod
    def require_version_one(cls, value: int) -> int:
        if value != 1:
            raise ValueError("must be 1")
        return value

    @model_validator(mode="after")
    def validate_title_routing(self) -> AppConfig:
        seen: set[str] = set()
        for mapping in self.titleRouting:
            marker = unicodedata.normalize("NFC", mapping.marker).casefold()
            if marker in seen:
                raise ValueError("titleRouting markers must be unique after normalization")
            seen.add(marker)
            if mapping.frontendRepository == mapping.backendRepository:
                raise ValueError("titleRouting frontend and backend repositories must differ")
            for repository in (mapping.frontendRepository, mapping.backendRepository):
                if repository not in self.repositories:
                    raise ValueError(f"titleRouting references unknown repository: {repository}")
        return self


class ValidationError(ConfigModel):
    field: str
    message: str


class ValidationResult(ConfigModel):
    valid: bool
    configVersion: int | None
    errors: list[ValidationError]
    redactedConfig: dict[str, Any] | None
