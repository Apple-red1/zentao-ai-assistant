from __future__ import annotations

import hashlib

from zentao_ai.state.models import OutboxRecord, OutboxStatus
from zentao_ai.zentao.models import BugSnapshot

from .models import CommentResult, RunContext


def canonical_comment(creator: str | None, text: str) -> str:
    return f"@{creator or 'reporter'}\n[zentao-ai:v2:information-request]\n{text.strip()}"


def write_information_comment(context: RunContext, snapshot: BugSnapshot, text: str) -> CommentResult:
    body = canonical_comment(snapshot.creator, text)
    key = hashlib.sha256(f"{snapshot.id}\0{snapshot.snapshot_version}\0{body}".encode()).hexdigest()
    if context.dryRun or context.readonly or context.scheduled or not context.config.permissions.commentEnabled:
        return CommentResult(str(snapshot.id), key, "SKIPPED")
    record = context.ledger.put_outbox(OutboxRecord(key, "comment", {"bugId": str(snapshot.id), "snapshotVersion": snapshot.snapshot_version, "contentHash": hashlib.sha256(body.encode()).hexdigest()}))
    if record.status in {OutboxStatus.CREATED, OutboxStatus.ALREADY_EXISTS}:
        return CommentResult(str(snapshot.id), key, record.status.value)
    if record.status is OutboxStatus.UNKNOWN:
        found = context.provider.reconcile_comment(key, snapshot.id, comment=body)
        status = OutboxStatus.ALREADY_EXISTS if found.status == "ALREADY_EXISTS" else OutboxStatus.CREATED if found.status == "CREATED" else OutboxStatus.UNKNOWN
        if status is not OutboxStatus.UNKNOWN:
            context.ledger.reconcile_outbox(
                key, status, str(found.comment_id) if found.comment_id else None
            )
        return CommentResult(str(snapshot.id), key, status.value)
    try:
        written = context.provider.add_bug_comment(snapshot.id, body, True, key)
    except (TimeoutError, ConnectionError):
        context.ledger.mark_outbox_result(key, OutboxStatus.UNKNOWN, None)
        return CommentResult(str(snapshot.id), key, "UNKNOWN")
    status = OutboxStatus.CREATED if written.created else OutboxStatus.ALREADY_EXISTS
    context.ledger.mark_outbox_result(key, status, str(written.comment_id) if written.comment_id else None)
    return CommentResult(str(snapshot.id), key, status.value)
