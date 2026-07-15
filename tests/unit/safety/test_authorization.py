import pytest
from zentao_ai.safety import ActionRequest, AuthorizationContext, AuthorizationRecord, authorize


def record(action, bug="B", parameters=None):
    return AuthorizationRecord(turnId="turn-1", source="user", action=action, bugId=bug, parameters=parameters or {})


@pytest.mark.parametrize("action", ["query", "analyze", "report"])
def test_read_only_actions_are_automatic(action):
    assert authorize(ActionRequest(action=action), AuthorizationContext()).allowed


def test_delete_and_equivalents_are_never_authorized():
    decision = authorize(ActionRequest(action="delete_bug", bugId="BUG-1"), AuthorizationContext(currentTurnId="turn-1", authorizationRecords=(record("delete_bug", "BUG-1"),)))
    assert not decision.allowed and decision.reason == "DELETE_UNCONDITIONALLY_FORBIDDEN"


def test_scheduled_protected_actions_and_untrusted_overrides_fail():
    assert not authorize(ActionRequest(action="comment", bugId="BUG-1"), AuthorizationContext(scheduled=True, commentEnabled=True)).allowed
    assert not authorize(ActionRequest(action="update_status", bugId="BUG-1", parameters={"status": "done"}, source="bug"), AuthorizationContext(bugId="BUG-1", parameters={"status": "done"})).allowed


def test_comment_step_status_and_code_write_matrix():
    comment = record("comment", parameters={"body": "fixed"})
    assert authorize(ActionRequest(action="comment", bugId="B", parameters={"body": "fixed"}), AuthorizationContext(currentTurnId="turn-1", authorizationRecords=(comment,), commentEnabled=True, snapshotStable=True, historyChecked=True, cooldownPassed=True, idempotencyPassed=True)).allowed
    assert authorize(ActionRequest(action="update_steps", bugId="B", parameters={"steps": "x"}), AuthorizationContext(currentTurnId="turn-1", authorizationRecords=(record("update_steps", parameters={"steps": "x"}),), stepUpdateEnabled=True)).allowed
    assert authorize(ActionRequest(action="update_status", bugId="B", parameters={"status": "done"}), AuthorizationContext(currentTurnId="turn-1", authorizationRecords=(record("update_status", parameters={"status": "done"}),))).allowed
    assert authorize(ActionRequest(action="write_code"), AuthorizationContext(codeWriteEnabled=True, routingUnique=True, repositoryGuardPassed=True)).allowed
    assert not authorize(ActionRequest(action="commit"), AuthorizationContext()).allowed


def test_authorization_compares_every_field_and_rejects_prior_turn_or_non_user_source():
    request = ActionRequest(action="update_status", bugId="B", parameters={"status": "done", "recipient": "alice"})
    base = record("update_status", parameters={"status": "done", "recipient": "alice"})
    assert authorize(request, AuthorizationContext(currentTurnId="turn-1", authorizationRecords=(base,))).allowed
    for changed in (
        base.model_copy(update={"turnId": "old"}),
        base.model_copy(update={"source": "bug"}),
        base.model_copy(update={"bugId": "OTHER"}),
        base.model_copy(update={"parameters": {"status": "done", "recipient": "mallory"}}),
    ):
        assert not authorize(request, AuthorizationContext(currentTurnId="turn-1", authorizationRecords=(changed,))).allowed


def test_step_update_requires_feature_flag_and_exact_complete_parameters():
    request = ActionRequest(action="update_steps", bugId="B", parameters={"steps": "x", "imagePath": "C:/x.png"})
    approved = record("update_steps", parameters={"steps": "x", "imagePath": "C:/x.png"})
    assert not authorize(request, AuthorizationContext(currentTurnId="turn-1", authorizationRecords=(approved,), stepUpdateEnabled=False)).allowed
    incomplete = record("update_steps", parameters={"steps": "x"})
    assert not authorize(request, AuthorizationContext(currentTurnId="turn-1", authorizationRecords=(incomplete,), stepUpdateEnabled=True)).allowed
