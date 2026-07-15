from __future__ import annotations

from typing import Protocol

from .models import (
    BugPage,
    BugSnapshot,
    BugStatistics,
    CommentWriteResult,
    HistoryPage,
    StepUpdateResult,
)


class ZentaoProvider(Protocol):
    def query_my_bugs(self, *, page: int = 1, page_size: int = 20) -> BugPage: ...
    def query_user_bugs(
        self, user: str, *, page: int = 1, page_size: int = 20
    ) -> BugPage: ...
    def query_bug_detail(self, bug_id: int | str) -> BugSnapshot: ...
    def query_bug_history(
        self, bug_id: int | str, *, page: int = 1, page_size: int = 20
    ) -> HistoryPage: ...
    def bug_statistics(self) -> BugStatistics: ...
    def add_bug_comment(
        self, bug_id: int | str, comment: str, confirm: bool, idempotency_key: str
    ) -> CommentWriteResult: ...
    def update_bug_steps(
        self, bug_id: int | str, steps: str, confirm: bool = True
    ) -> StepUpdateResult: ...
    def update_bug_steps_with_image(
        self,
        bug_id: int | str,
        steps: str,
        image: bytes,
        filename: str,
        content_type: str,
        confirm: bool = True,
    ) -> StepUpdateResult: ...
    def reconcile_comment(
        self, idempotency_key: str, bug_id: int | str, *, comment: str | None = None
    ) -> CommentWriteResult: ...
