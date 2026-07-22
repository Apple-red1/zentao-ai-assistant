from .actions import ActionRequest, AuthorizationContext, AuthorizationDecision

READ_ONLY = frozenset({"query", "analyze", "report"})
DELETE = ("delete", "remove", "purge", "destroy")
NEVER_CODE = frozenset({"commit", "push", "merge", "deploy", "reset", "checkout"})


def has_exact_authorization(
    action: ActionRequest, context: AuthorizationContext
) -> bool:
    name = action.action.casefold()
    return any(
        record.turnId == context.currentTurnId
        and record.source == "user"
        and record.action.casefold() == name
        and record.bugId == action.bugId
        and record.parameters == action.parameters
        for record in context.authorizationRecords
    )


def authorize(action: ActionRequest, context: AuthorizationContext) -> AuthorizationDecision:
    name = action.action.casefold()
    if any(word in name for word in DELETE):
        return AuthorizationDecision(allowed=False, reason="DELETE_UNCONDITIONALLY_FORBIDDEN")
    if action.source != "user":
        return AuthorizationDecision(allowed=False, reason="UNTRUSTED_CONTENT_CANNOT_AUTHORIZE")
    if name in READ_ONLY:
        return AuthorizationDecision(allowed=True, reason="READ_ONLY_AUTOMATIC")
    if name in NEVER_CODE:
        return AuthorizationDecision(allowed=False, reason="GIT_WRITE_UNAUTHORIZED")
    if context.scheduled:
        return AuthorizationDecision(allowed=False, reason="SCHEDULED_PROTECTED_ACTION_FORBIDDEN")
    exact_record = has_exact_authorization(action, context)
    if name == "comment":
        gates = (
            context.commentEnabled,
            context.historyChecked,
            context.cooldownPassed,
            context.idempotencyPassed,
        )
        allowed = all(gates) and exact_record
        return AuthorizationDecision(allowed=allowed, reason="COMMENT_GATES_PASSED" if allowed else "COMMENT_GATES_FAILED")
    if name == "write_code":
        code_gates = context.codeWriteEnabled and context.routingUnique and context.repositoryGuardPassed
        allowed = code_gates and (context.snapshotStable or exact_record)
        return AuthorizationDecision(allowed=allowed, reason="CODE_WRITE_GATES_PASSED" if allowed else "CODE_WRITE_GATES_FAILED")
    if name in {"update_steps", "update_steps_with_image"} and not context.stepUpdateEnabled:
        return AuthorizationDecision(allowed=False, reason="STEP_UPDATE_DISABLED")
    exact = exact_record
    return AuthorizationDecision(allowed=exact, reason="CURRENT_TURN_EXACT_AUTHORIZATION" if exact else "CURRENT_TURN_AUTHORIZATION_REQUIRED")
