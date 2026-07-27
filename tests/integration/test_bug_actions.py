from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from zentao_ai.actions import BugActionService
from zentao_ai.models import (
    BugChanges,
    BugRecord,
    Settings,
    UserRef,
    WriteAuthorization,
    ZentaoSettings,
)


@dataclass
class RecordingClient:
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def request_json(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append({"method": method, "path": path, **kwargs})
        return {"status": "success"}


class SnapshotBugs:
    def __init__(self, before: BugRecord, after: BugRecord | None = None) -> None:
        self.snapshots = [before, after or before]

    async def get_bug(self, bug_id: int) -> BugRecord:
        return self.snapshots.pop(0)


@dataclass
class RecordingUsers:
    force_refresh: bool = False

    async def resolve(
        self,
        query: str,
        kind: str = "all",
        *,
        force_refresh: bool = False,
    ) -> UserRef:
        self.force_refresh = force_refresh
        return UserRef(id="7", account="lisi", real_name="李四", kind="inside")


def settings() -> Settings:
    return Settings(
        version=1,
        zentao=ZentaoSettings(base_url="https://z.example", account="me"),
    )


def bug(**changes: object) -> BugRecord:
    values: dict[str, object] = {
        "id": 123,
        "title": "Original title",
        "status": "active",
        "assigned_to": "me",
        "opened_build_ids": ["trunk"],
    }
    values.update(changes)
    return BugRecord.model_validate(values)


async def test_comment_preserves_required_fields_without_old_payload() -> None:
    client = RecordingClient()
    service = BugActionService(client, SnapshotBugs(bug()), RecordingUsers(), settings())

    result = await service.add_comment(
        123,
        "请补充日志",
        WriteAuthorization(confirm=True, bug_id=123, action="comment"),
    )

    assert result.status == "success"
    assert client.calls == [
        {
            "method": "PUT",
            "path": "/bugs/123",
            "json": {
                "title": "Original title",
                "openedBuild": ["trunk"],
                "comment": "请补充日志",
            },
            "write": True,
        }
    ]


async def test_assign_refreshes_user_and_uses_assign_to_endpoint() -> None:
    client = RecordingClient()
    users = RecordingUsers()
    service = BugActionService(
        client,
        SnapshotBugs(bug(), bug(assigned_to="lisi")),
        users,
        settings(),
    )

    result = await service.assign_bug(
        123,
        "李四",
        "请处理",
        WriteAuthorization(confirm=True, bug_id=123, action="assign"),
    )

    assert result.after is not None and result.after.assigned_to == "lisi"
    assert users.force_refresh is True
    assert client.calls[0]["path"] == "/bugs/123/assignTo"
    assert client.calls[0]["json"] == {"assignedTo": "lisi", "comment": "请处理"}


async def test_edit_maps_only_supported_fields() -> None:
    client = RecordingClient()
    service = BugActionService(
        client,
        SnapshotBugs(bug(), bug(title="Updated", severity=1)),
        RecordingUsers(),
        settings(),
    )

    await service.edit_bug(
        123,
        BugChanges(title="Updated", severity=1),
        WriteAuthorization(confirm=True, bug_id=123, action="edit"),
    )

    assert client.calls[0]["json"] == {"title": "Updated", "severity": 1}
