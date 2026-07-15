from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class OutboxStatus(str, Enum):
    PENDING = "PENDING"
    CREATED = "CREATED"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class LeaseResult:
    acquired: bool
    lease_id: str
    owner: str
    expires_at: str
    previous_owner: str | None = None


@dataclass(frozen=True)
class CommentRecord:
    idempotency_key: str
    bug_id: str
    payload: Any
    payload_hash: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class OutboxRecord:
    idempotency_key: str
    run_kind: str
    payload: Any
    status: OutboxStatus = OutboxStatus.PENDING
    external_id: str | None = None
    payload_hash: str = ""
    created_at: str = ""


class StateError(Exception):
    pass


class IdempotencyConflict(StateError):
    pass


class PayloadRejected(StateError):
    pass
