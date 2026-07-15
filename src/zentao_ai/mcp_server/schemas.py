from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from zentao_ai.safety.actions import AuthorizationRecord

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PagingInput(StrictInput):
    page: int = Field(1, ge=1)
    pageSize: int = Field(20, ge=1, le=100)


class QueryMyBugsInput(PagingInput):
    pass


class QueryUserBugsInput(PagingInput):
    user: NonEmpty


class QueryBugDetailInput(StrictInput):
    bugId: int | NonEmpty


class QueryBugHistoryInput(PagingInput):
    bugId: int | NonEmpty


class BugStatisticsInput(StrictInput):
    pass


class WriteContext(StrictInput):
    turnId: NonEmpty
    authorizationRecords: tuple[AuthorizationRecord, ...]
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
    steps: tuple[ReproductionStepInput, ...] = Field(min_length=1)
    confirm: Literal[True]


class UpdateStepsWithImageInput(UpdateStepsInput):
    imagePath: Path

    @field_validator("imagePath")
    @classmethod
    def absolute_local_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("imagePath must be an absolute local path")
        return value


INPUT_MODELS: dict[str, type[StrictInput]] = {
    "query_my_bugs": QueryMyBugsInput,
    "query_user_bugs": QueryUserBugsInput,
    "query_bug_detail": QueryBugDetailInput,
    "query_bug_history": QueryBugHistoryInput,
    "bug_statistics": BugStatisticsInput,
    "add_bug_comment": AddCommentInput,
    "update_bug_steps": UpdateStepsInput,
    "update_bug_steps_with_image": UpdateStepsWithImageInput,
}
