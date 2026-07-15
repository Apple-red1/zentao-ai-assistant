from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, cast
from zoneinfo import ZoneInfo

from zentao_ai.config.models import AppConfig
from zentao_ai.safety.actions import AuthorizationRecord
from zentao_ai.state.models import LeaseResult, OutboxRecord, OutboxStatus
from zentao_ai.zentao.models import (
    BugPage,
    BugSnapshot,
    CommentWriteResult,
    HistoryPage,
    StepUpdateResult,
)


class AnalysisPhase(str, Enum):
    PRECHECK = "PRECHECK"
    FINAL_DECISION = "FINAL_DECISION"
    FINAL = "FINAL_DECISION"


class Decision(str, Enum):
    PROCEED_TO_EVIDENCE = "PROCEED_TO_EVIDENCE"
    FIX_CANDIDATE = "FIX_CANDIDATE"
    NEEDS_REPORTER_INFO = "NEEDS_REPORTER_INFO"
    NEEDS_ENGINEER_REVIEW = "NEEDS_ENGINEER_REVIEW"
    TOOL_OR_PERMISSION_GAP = "TOOL_OR_PERMISSION_GAP"
    PATCH_RETAINED_FOR_HUMAN_VALIDATION = "PATCH_RETAINED_FOR_HUMAN_VALIDATION"


@dataclass(frozen=True)
class SnapshotContext:
    businessDate: date
    snapshotCutoff: datetime
    timezone: str = "Asia/Shanghai"

    @classmethod
    def capture(cls, now: datetime) -> SnapshotContext:
        zone = ZoneInfo("Asia/Shanghai")
        aware = now.replace(tzinfo=zone) if now.tzinfo is None else now.astimezone(zone)
        return cls(aware.date(), aware, "Asia/Shanghai")


@dataclass(frozen=True)
class AnalysisSignal:
    evidenceComplete: bool = False
    fixCandidate: bool = False
    needsReporterInfo: bool = False
    needsEngineerReview: bool = False
    toolOrPermissionGap: bool = False
    patchRetained: bool = False


@dataclass(frozen=True)
class BugAnalysisResult:
    decision: Decision
    phase: AnalysisPhase
    reasons: tuple[str, ...] = ()


class PatchOutcome(str, Enum):
    APPLIED = "APPLIED"
    TESTS_FAILED = "TESTS_FAILED"
    FAILED = "FAILED"


class Provider(Protocol):
    def query_my_bugs(
        self, *, scope_names: tuple[str, ...], page: int = 1, page_size: int = 20
    ) -> BugPage: ...
    def query_user_bugs(
        self,
        user: str,
        *,
        scope_names: tuple[str, ...],
        page: int = 1,
        page_size: int = 20,
    ) -> BugPage: ...
    def query_bug_detail(self, bug_id: int | str) -> BugSnapshot: ...
    def query_bug_history(
        self, bug_id: int | str, *, page: int = 1, page_size: int = 20
    ) -> HistoryPage: ...
    def add_bug_comment(
        self, bug_id: int | str, comment: str, confirm: bool, idempotency_key: str
    ) -> CommentWriteResult: ...
    def reconcile_comment(
        self, idempotency_key: str, bug_id: int | str, *, comment: str | None = None
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


class Ledger(Protocol):
    def acquire_lease(
        self, business_date: date, run_kind: str, owner: str, ttl_seconds: int
    ) -> LeaseResult: ...
    def release_lease(self, lease_id: str, status: object) -> None: ...
    def put_checkpoint(
        self, business_date: date, run_kind: str, payload: object
    ) -> None: ...
    def put_outbox(self, record: OutboxRecord) -> OutboxRecord: ...
    def mark_outbox_result(
        self, key: str, status: OutboxStatus, external_id: str | None
    ) -> OutboxRecord: ...
    def reconcile_outbox(
        self, key: str, status: OutboxStatus, external_id: str | None
    ) -> OutboxRecord: ...


class PatchExecutor(Protocol):
    def reproduce(self, repository: object, bug: object) -> bool: ...
    def apply(self, repository: object, bug: object) -> PatchOutcome: ...
    def test(self, repository: object, commands: Sequence[str]) -> bool: ...
    def diff_safe(self, repository: object) -> bool: ...


class RepositoryPort(Protocol):
    def preflight(self, config: AppConfig, routing: object) -> object: ...
    def unchanged(self, lease: object) -> bool: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...


class ReportSink(Protocol):
    def write(self, payload: dict[str, object]) -> None: ...


@dataclass(frozen=True)
class Failure:
    bugId: str
    category: str
    message: str


@dataclass(frozen=True)
class BugRunResult:
    bugId: str
    snapshotVersion: str
    decision: Decision


@dataclass(frozen=True)
class CommentResult:
    bugId: str
    idempotencyKey: str
    status: str


@dataclass(frozen=True)
class ResolutionCommentPayload:
    summary: str
    testResults: tuple[TestResult, ...] = ()


@dataclass(frozen=True)
class TestResult:
    command: str
    passed: bool


@dataclass(frozen=True)
class RunResult:
    businessDate: str
    snapshotCutoff: str
    coverage: int
    completeness: str
    bugResults: tuple[BugRunResult, ...] = ()
    commentResults: tuple[CommentResult, ...] = ()
    testResults: tuple[TestResult, ...] = ()
    failures: tuple[Failure, ...] = ()
    scopeNames: tuple[str, ...] = ()
    members: tuple[str, ...] = ()
    coverageTotal: int | None = None
    truncated: bool = False

    def to_v2_payload(self) -> dict[str, object]:
        def item(v: object) -> dict[str, object]:
            result = asdict(cast(Any, v))
            return {
                k: (x.value if isinstance(x, Enum) else x) for k, x in result.items()
            }

        return {
            "schemaVersion": "v2",
            "businessDate": self.businessDate,
            "snapshotCutoff": self.snapshotCutoff,
            "coverage": self.coverage,
            "coverageTotal": self.coverageTotal,
            "truncated": self.truncated,
            "completeness": self.completeness,
            "scopeNames": list(self.scopeNames),
            "members": list(self.members),
            "bugResults": [item(x) for x in self.bugResults],
            "commentResults": [item(x) for x in self.commentResults],
            "testResults": [item(x) for x in self.testResults],
            "failures": [item(x) for x in self.failures],
        }


PersonalRunResult = RunResult
TeamRunResult = RunResult


@dataclass(frozen=True)
class RepairResult:
    bugId: str
    decision: Decision
    success: bool = False
    localCandidateSuccess: bool = False
    commentDelivered: bool = False
    localChangesRetained: bool = False
    reasons: tuple[str, ...] = ()
    commentResult: CommentResult | None = None
    testResults: tuple[TestResult, ...] = ()


@dataclass(frozen=True)
class RunContext:
    config: AppConfig
    provider: Provider
    ledger: Ledger
    now: Clock
    owner: str
    analysis: (
        Callable[[object, Sequence[object], AnalysisPhase], AnalysisSignal] | None
    ) = None
    repository: RepositoryPort | None = None
    patchExecutor: PatchExecutor | None = None
    reportSink: ReportSink | None = None
    snapshot: SnapshotContext | None = None
    dryRun: bool = False
    readonly: bool = False
    scheduled: bool = False
    team: bool = False
    currentTurnId: str | None = None
    authorizationRecords: tuple[AuthorizationRecord, ...] = ()
    authorizedImagePaths: tuple[Path, ...] = ()
    snapshotStable: bool = False
    historyChecked: bool = False
    cooldownPassed: bool = False
    idempotencyPassed: bool = False
