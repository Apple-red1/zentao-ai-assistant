from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from zentao_ai.config.models import AppConfig
from zentao_ai.safety.actions import AuthorizationRecord


class AnalysisPhase(str, Enum):
    PRECHECK = "PRECHECK"
    FINAL = "FINAL"


class Decision(str, Enum):
    PROCEED_TO_EVIDENCE = "PROCEED_TO_EVIDENCE"
    FIX_CANDIDATE = "FIX_CANDIDATE"
    NEEDS_REPORTER_INFO = "NEEDS_REPORTER_INFO"
    NEEDS_ENGINEER_REVIEW = "NEEDS_ENGINEER_REVIEW"
    TOOL_OR_PERMISSION_GAP = "TOOL_OR_PERMISSION_GAP"
    PATCH_RETAINED_FOR_HUMAN_VALIDATION = "PATCH_RETAINED_FOR_HUMAN_VALIDATION"


@dataclass(frozen=True)
class AnalysisSignal:
    evidenceComplete: bool = False
    fixCandidate: bool = False
    needsReporterInfo: bool = False
    needsEngineerReview: bool = False
    toolOrPermissionGap: bool = False


@dataclass(frozen=True)
class BugAnalysisResult:
    decision: Decision
    phase: AnalysisPhase
    reasons: tuple[str, ...] = ()


class PatchOutcome(str, Enum):
    APPLIED = "APPLIED"
    TESTS_FAILED = "TESTS_FAILED"
    FAILED = "FAILED"


class PatchExecutor(Protocol):
    def reproduce(self, repository: object, bug: object) -> bool: ...
    def apply(self, repository: object, bug: object) -> PatchOutcome: ...
    def test(self, repository: object, commands: Sequence[str]) -> bool: ...
    def diff_safe(self, repository: object) -> bool: ...


class RepositoryPort(Protocol):
    def preflight(self, config: AppConfig, routing: object) -> object: ...
    def unchanged(self, lease: object) -> bool: ...


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
class RunResult:
    businessDate: str
    snapshotCutoff: str
    coverage: int
    completeness: str
    bugResults: tuple[BugRunResult, ...] = ()
    commentResults: tuple[object, ...] = ()
    testResults: tuple[object, ...] = ()
    failures: tuple[Failure, ...] = ()
    scopeNames: tuple[str, ...] = ()
    members: tuple[str, ...] = ()

    def to_v2_payload(self) -> dict[str, object]:
        return {"businessDate": self.businessDate, "snapshotCutoff": self.snapshotCutoff, "coverage": self.coverage, "completeness": self.completeness, "bugResults": [item.__dict__ | {"decision": item.decision.value} for item in self.bugResults], "commentResults": list(self.commentResults), "testResults": list(self.testResults), "failures": [item.__dict__ for item in self.failures]}


PersonalRunResult = RunResult
TeamRunResult = RunResult


@dataclass(frozen=True)
class CommentResult:
    bugId: str
    idempotencyKey: str
    status: str


@dataclass(frozen=True)
class RepairResult:
    bugId: str
    decision: Decision
    success: bool = False
    localChangesRetained: bool = False
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunContext:
    config: AppConfig
    provider: Any
    ledger: Any
    now: Callable[[], datetime]
    owner: str
    analysis: Callable[[object, Sequence[object], AnalysisPhase], AnalysisSignal] | None = None
    repository: RepositoryPort | None = None
    patchExecutor: PatchExecutor | None = None
    dryRun: bool = False
    readonly: bool = False
    scheduled: bool = False
    currentTurnId: str | None = None
    authorizationRecords: tuple[AuthorizationRecord, ...] = ()
    authorizedImagePaths: tuple[Path, ...] = ()
