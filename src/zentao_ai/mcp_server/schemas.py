from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    StringConstraints,
    field_validator,
)

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, strict=True)


class PagingInput(StrictInput):
    page: int = Field(1, ge=1)
    pageSize: int = Field(20, ge=1, le=100)


class QueryMyBugsInput(PagingInput):
    titleTag: NonEmpty | None = None
    status: Literal["all", "unclosed"] = "unclosed"


class QueryUserBugsInput(PagingInput):
    user: NonEmpty
    scopeMode: Literal["team-report", "session-visible"] = "team-report"
    status: Literal["all", "unclosed"] = "all"


class QueryBugsByTitleInput(PagingInput):
    titleKeyword: NonEmpty
    status: Literal["all", "unclosed"] = "unclosed"


class QueryBugDetailInput(StrictInput):
    bugId: int | NonEmpty


class QueryBugHistoryInput(PagingInput):
    bugId: int | NonEmpty


class BugStatisticsInput(StrictInput):
    pass


class ToolAuthorization(StrictInput):
    turnId: NonEmpty
    source: Literal["user"]
    action: Literal["comment", "update_steps", "update_steps_with_image"]
    bugId: StrictInt | StrictStr
    parameters: dict[StrictStr, object]
    authorizedImagePaths: list[StrictStr]

    @field_validator("authorizedImagePaths")
    @classmethod
    def absolute_authorized_paths(cls, values: list[str]) -> list[str]:
        for value in values:
            if not value.strip() or "\x00" in value or not Path(value).is_absolute():
                raise ValueError(
                    "authorizedImagePaths must contain absolute local paths"
                )
        return values


class WriteContext(StrictInput):
    currentTurnId: NonEmpty
    authorization: ToolAuthorization
    scheduled: bool = False
    nonInteractive: bool = False


class AddCommentInput(WriteContext):
    bugId: int | NonEmpty
    comment: NonEmpty
    confirm: Literal[True]
    idempotencyKey: NonEmpty
    snapshotStable: bool
    historyChecked: bool
    cooldownPassed: bool
    idempotencyPassed: bool


class ReproductionStepInput(StrictInput):
    action: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3)]
    expected: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3)]


class UpdateStepsInput(WriteContext):
    bugId: int | NonEmpty
    steps: list[ReproductionStepInput] = Field(min_length=1)
    confirm: Literal[True]


class UpdateStepsWithImageInput(UpdateStepsInput):
    imagePath: StrictStr

    @field_validator("imagePath")
    @classmethod
    def absolute_local_path(cls, value: str) -> str:
        if not value.strip() or "\x00" in value or not Path(value).is_absolute():
            raise ValueError("imagePath must be an absolute local path")
        return value


INPUT_MODELS: dict[str, type[StrictInput]] = {
    "query_my_bugs": QueryMyBugsInput,
    "query_user_bugs": QueryUserBugsInput,
    "query_bugs_by_title": QueryBugsByTitleInput,
    "query_bug_detail": QueryBugDetailInput,
    "query_bug_history": QueryBugHistoryInput,
    "bug_statistics": BugStatisticsInput,
    "add_bug_comment": AddCommentInput,
    "update_bug_steps": UpdateStepsInput,
    "update_bug_steps_with_image": UpdateStepsWithImageInput,
}
