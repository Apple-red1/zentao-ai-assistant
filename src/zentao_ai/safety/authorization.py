from .actions import ActionRequest, AuthorizationContext, AuthorizationDecision

READ_ONLY = frozenset({"query", "analyze", "report"})
DELETE = ("delete", "remove", "purge", "destroy")
NEVER_CODE = frozenset({"commit", "push", "merge", "deploy", "reset", "checkout"})


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
    if name == "comment":
        gates = (context.commentEnabled, context.snapshotStable, context.historyChecked, context.cooldownPassed, context.idempotencyPassed)
        return AuthorizationDecision(allowed=all(gates), reason="COMMENT_GATES_PASSED" if all(gates) else "COMMENT_GATES_FAILED")
    if name == "write_code":
        code_gates = context.codeWriteEnabled and context.routingUnique and context.repositoryGuardPassed
        return AuthorizationDecision(allowed=code_gates, reason="CODE_WRITE_GATES_PASSED" if code_gates else "CODE_WRITE_GATES_FAILED")
    exact = name in context.explicitActions and action.bugId == context.bugId and action.parameters == context.parameters
    return AuthorizationDecision(allowed=exact, reason="CURRENT_TURN_EXACT_AUTHORIZATION" if exact else "CURRENT_TURN_AUTHORIZATION_REQUIRED")
