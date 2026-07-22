from zentao_ai.zentao.models import BugSnapshot


def unstable_snapshot_matches(before: BugSnapshot, after: BugSnapshot) -> bool:
    if str(before.id) != str(after.id):
        return False
    if before.snapshot_stable or after.snapshot_stable:
        return before.snapshot_version == after.snapshot_version
    return (
        before.status == after.status
        and before.assignee == after.assignee
        and before.title == after.title
        and before.priority == after.priority
    )
