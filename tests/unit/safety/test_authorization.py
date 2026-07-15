import pytest
from zentao_ai.safety import ActionRequest, AuthorizationContext, authorize


@pytest.mark.parametrize("action", ["query", "analyze", "report"])
def test_read_only_actions_are_automatic(action):
    assert authorize(ActionRequest(action=action), AuthorizationContext()).allowed


def test_delete_and_equivalents_are_never_authorized():
    decision = authorize(ActionRequest(action="delete_bug", bugId="BUG-1"), AuthorizationContext(explicitActions=("delete_bug",)))
    assert not decision.allowed and decision.reason == "DELETE_UNCONDITIONALLY_FORBIDDEN"


def test_scheduled_protected_actions_and_untrusted_overrides_fail():
    assert not authorize(ActionRequest(action="comment", bugId="BUG-1"), AuthorizationContext(scheduled=True, commentEnabled=True)).allowed
    assert not authorize(ActionRequest(action="update_status", bugId="BUG-1", parameters={"status": "done"}, source="bug"), AuthorizationContext(explicitActions=("update_status",), bugId="BUG-1", parameters={"status": "done"})).allowed


def test_comment_step_status_and_code_write_matrix():
    assert authorize(ActionRequest(action="comment", bugId="B"), AuthorizationContext(commentEnabled=True, snapshotStable=True, historyChecked=True, cooldownPassed=True, idempotencyPassed=True)).allowed
    assert authorize(ActionRequest(action="update_steps", bugId="B"), AuthorizationContext(explicitActions=("update_steps",), bugId="B")).allowed
    assert authorize(ActionRequest(action="update_status", bugId="B", parameters={"status": "done"}), AuthorizationContext(explicitActions=("update_status",), bugId="B", parameters={"status": "done"})).allowed
    assert authorize(ActionRequest(action="write_code"), AuthorizationContext(codeWriteEnabled=True, routingUnique=True, repositoryGuardPassed=True)).allowed
    assert not authorize(ActionRequest(action="commit"), AuthorizationContext(explicitActions=("commit",))).allowed
