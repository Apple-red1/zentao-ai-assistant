from __future__ import annotations

import hashlib

from zentao_ai.state.models import OutboxRecord, OutboxStatus
from zentao_ai.zentao.models import BugSnapshot

from .models import CommentResult, RunContext
from zentao_ai.safety.actions import ActionRequest, AuthorizationContext
from zentao_ai.safety.authorization import authorize


def canonical_comment(creator: str, text: str) -> str:
    if not creator.strip():
        raise ValueError("creator.account is required")
    return f"@{creator.strip()}\n[zentao-ai:v2:information-request]\n{text.strip()}"


def write_information_comment(
    context: RunContext, snapshot: BugSnapshot, text: str
) -> CommentResult:
    creator = snapshot.creator
    raw_creator = snapshot.raw.get("creator")
    if isinstance(raw_creator, dict):
        creator = str(raw_creator.get("account") or "")
    body = canonical_comment(creator or "", text)
    key = hashlib.sha256(
        f"{snapshot.id}\0{snapshot.snapshot_version}\0{body}".encode()
    ).hexdigest()
    gates = (
        context.snapshotStable,
        context.historyChecked,
        context.cooldownPassed,
        context.idempotencyPassed,
    )
    auth = AuthorizationContext(
        scheduled=context.scheduled,
        commentEnabled=context.config.permissions.commentEnabled,
        snapshotStable=context.snapshotStable,
        historyChecked=context.historyChecked,
        cooldownPassed=context.cooldownPassed,
        idempotencyPassed=context.idempotencyPassed,
        currentTurnId=context.currentTurnId,
        authorizationRecords=context.authorizationRecords,
    )
    permitted = authorize(
        ActionRequest(
            action="comment", bugId=str(snapshot.id), parameters={"comment": body}
        ),
        auth,
    ).allowed
    if context.dryRun or context.readonly or not all(gates) or not permitted:
        return CommentResult(str(snapshot.id), key, "SKIPPED")
    record = context.ledger.put_outbox(
        OutboxRecord(
            key,
            "comment",
            {
                "bugId": str(snapshot.id),
                "snapshotVersion": snapshot.snapshot_version,
                "contentHash": hashlib.sha256(body.encode()).hexdigest(),
            },
        )
    )
    if record.status in {OutboxStatus.CREATED, OutboxStatus.ALREADY_EXISTS}:
        return CommentResult(str(snapshot.id), key, record.status.value)
    if record.status is OutboxStatus.UNKNOWN:
        found = context.provider.reconcile_comment(key, snapshot.id, comment=body)
        status = (
            OutboxStatus.ALREADY_EXISTS
            if found.status == "ALREADY_EXISTS"
            else OutboxStatus.CREATED
            if found.status == "CREATED"
            else OutboxStatus.UNKNOWN
        )
        if status is not OutboxStatus.UNKNOWN:
            context.ledger.reconcile_outbox(
                key, status, str(found.comment_id) if found.comment_id else None
            )
        return CommentResult(str(snapshot.id), key, status.value)
    if record.status is not OutboxStatus.PENDING:
        return CommentResult(str(snapshot.id), key, record.status.value)
    try:
        written = context.provider.add_bug_comment(snapshot.id, body, True, key)
    except (TimeoutError, ConnectionError):
        context.ledger.mark_outbox_result(key, OutboxStatus.UNKNOWN, None)
        found = context.provider.reconcile_comment(key, snapshot.id, comment=body)
        if found.status in {"CREATED", "ALREADY_EXISTS"}:
            status = OutboxStatus(found.status)
            context.ledger.reconcile_outbox(
                key, status, str(found.comment_id) if found.comment_id else None
            )
            return CommentResult(str(snapshot.id), key, status.value)
        return CommentResult(str(snapshot.id), key, OutboxStatus.UNKNOWN.value)
    status = OutboxStatus.CREATED if written.created else OutboxStatus.ALREADY_EXISTS
    context.ledger.mark_outbox_result(
        key, status, str(written.comment_id) if written.comment_id else None
    )
    return CommentResult(str(snapshot.id), key, status.value)
