from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol

from zentao_ai.errors import ErrorCode, ZentaoError
from zentao_ai.models import (
    BugChanges,
    BugRecord,
    BugWriteResult,
    Settings,
    UserRef,
    WriteAuthorization,
)

QueryValue = str | int | float | bool | None
WriteAction = Literal["comment", "edit", "activate", "assign"]


class JsonClient(Protocol):
    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryValue] | None = None,
        json: Mapping[str, object] | None = None,
        write: bool = False,
    ) -> dict[str, Any]: ...


class BugReader(Protocol):
    async def get_bug(self, bug_id: int) -> BugRecord: ...


class UserResolver(Protocol):
    async def resolve(
        self,
        query: str,
        kind: Literal["inside", "outside", "all"] = "all",
        *,
        force_refresh: bool = False,
    ) -> UserRef: ...


class BugActionService:
    def __init__(
        self,
        client: JsonClient,
        bugs: BugReader,
        users: UserResolver,
        settings: Settings,
    ) -> None:
        self._client = client
        self._bugs = bugs
        self._users = users
        self._settings = settings

    def validate_authorization(
        self,
        authorization: WriteAuthorization,
        *,
        expected_action: WriteAction,
        bug_id: int,
    ) -> None:
        if not self._settings.writes.enabled:
            raise ZentaoError(
                ErrorCode.CAPABILITY_UNAVAILABLE,
                "ZenTao write operations are disabled in local configuration.",
            )
        if authorization.confirm is not True:
            raise ZentaoError(
                ErrorCode.VALIDATION_ERROR,
                "This write requires explicit confirmation in the current request.",
            )
        if authorization.action != expected_action or authorization.bug_id != bug_id:
            raise ZentaoError(
                ErrorCode.VALIDATION_ERROR,
                "Write confirmation does not match the requested Bug action.",
            )

    async def add_comment(
        self,
        bug_id: int,
        comment: str,
        authorization: WriteAuthorization,
    ) -> BugWriteResult:
        self.validate_authorization(
            authorization,
            expected_action="comment",
            bug_id=bug_id,
        )
        text = comment.strip()
        if not text:
            raise ZentaoError(ErrorCode.VALIDATION_ERROR, "Comment cannot be empty.")
        before = await self._bugs.get_bug(bug_id)
        if not before.title or not before.opened_build_ids:
            raise ZentaoError(
                ErrorCode.CAPABILITY_UNAVAILABLE,
                "The Bug does not expose the title and opened build required for a safe comment.",
            )
        await self._client.request_json(
            "PUT",
            f"/bugs/{bug_id}",
            json={
                "title": before.title,
                "openedBuild": before.opened_build_ids,
                "comment": text,
            },
            write=True,
        )
        after = await self._bugs.get_bug(bug_id)
        return BugWriteResult(
            status="success",
            before=before,
            after=after,
            changed_fields=["comment"],
            message=f"已为 Bug #{bug_id} 添加备注。",
        )

    async def edit_bug(
        self,
        bug_id: int,
        changes: BugChanges,
        authorization: WriteAuthorization,
    ) -> BugWriteResult:
        self.validate_authorization(
            authorization,
            expected_action="edit",
            bug_id=bug_id,
        )
        before = await self._bugs.get_bug(bug_id)
        source = changes.model_dump(exclude_none=True)
        names = {
            "bug_type": "type",
            "opened_builds": "openedBuild",
            "project_id": "project",
            "execution_id": "execution",
            "story_id": "story",
        }
        payload = {names.get(key, key): value for key, value in source.items()}
        await self._client.request_json(
            "PUT",
            f"/bugs/{bug_id}",
            json=payload,
            write=True,
        )
        after = await self._bugs.get_bug(bug_id)
        self._verify_edit(after, changes)
        return BugWriteResult(
            status="success",
            before=before,
            after=after,
            changed_fields=sorted(source),
            message=f"已更新 Bug #{bug_id}。",
        )

    async def activate_bug(
        self,
        bug_id: int,
        opened_builds: list[str],
        authorization: WriteAuthorization,
        *,
        assigned_to: str | None = None,
        comment: str | None = None,
    ) -> BugWriteResult:
        self.validate_authorization(
            authorization,
            expected_action="activate",
            bug_id=bug_id,
        )
        before = await self._bugs.get_bug(bug_id)
        if before.status.casefold() not in {"resolved", "closed"}:
            raise ZentaoError(
                ErrorCode.VALIDATION_ERROR,
                "Only resolved or closed Bugs can be activated.",
            )
        builds = [item.strip() for item in opened_builds if item.strip()]
        if not builds:
            raise ZentaoError(ErrorCode.VALIDATION_ERROR, "Activation requires an opened build.")
        payload: dict[str, object] = {"openedBuild": builds}
        if assigned_to:
            user = await self._users.resolve(assigned_to, force_refresh=True)
            payload["assignedTo"] = user.account
        if comment and comment.strip():
            payload["comment"] = comment.strip()
        await self._client.request_json(
            "PUT",
            f"/bugs/{bug_id}/activate",
            json=payload,
            write=True,
        )
        after = await self._bugs.get_bug(bug_id)
        if after.status.casefold() in {"resolved", "closed"}:
            raise ZentaoError(
                ErrorCode.CAPABILITY_UNAVAILABLE,
                "ZenTao accepted the request but the Bug is not active in the latest snapshot.",
            )
        return BugWriteResult(
            status="success",
            before=before,
            after=after,
            changed_fields=sorted(payload),
            message=f"已激活 Bug #{bug_id}。",
        )

    async def assign_bug(
        self,
        bug_id: int,
        assigned_to: str,
        comment: str | None,
        authorization: WriteAuthorization,
    ) -> BugWriteResult:
        self.validate_authorization(
            authorization,
            expected_action="assign",
            bug_id=bug_id,
        )
        before = await self._bugs.get_bug(bug_id)
        if before.status.casefold() == "closed":
            raise ZentaoError(ErrorCode.VALIDATION_ERROR, "A closed Bug cannot be assigned.")
        user = await self._users.resolve(assigned_to, force_refresh=True)
        payload: dict[str, object] = {"assignedTo": user.account}
        if comment and comment.strip():
            payload["comment"] = comment.strip()
        await self._client.request_json(
            "PUT",
            f"/bugs/{bug_id}/assignTo",
            json=payload,
            write=True,
        )
        after = await self._bugs.get_bug(bug_id)
        if after.assigned_to != user.account:
            raise ZentaoError(
                ErrorCode.CAPABILITY_UNAVAILABLE,
                "ZenTao accepted the request but the latest assignee does not match.",
            )
        return BugWriteResult(
            status="success",
            before=before,
            after=after,
            changed_fields=["assigned_to"]
            + (["comment"] if comment and comment.strip() else []),
            message=(
                f"已将 Bug #{bug_id} 指派给 "
                f"{user.real_name or user.account} ({user.account})。"
            ),
        )

    @staticmethod
    def _verify_edit(after: BugRecord, changes: BugChanges) -> None:
        checks: dict[str, object] = {
            "title": after.title,
            "severity": after.severity,
            "priority": after.priority,
            "bug_type": after.bug_type,
            "opened_builds": after.opened_build_ids,
            "project_id": after.project_id,
            "execution_id": after.execution_id,
        }
        for key, expected in changes.model_dump(exclude_none=True).items():
            if key == "story_id" or key == "steps":
                continue
            actual = checks[key]
            if isinstance(expected, list):
                matches = isinstance(actual, list) and [str(item) for item in actual] == [
                    str(item) for item in expected
                ]
            else:
                matches = str(actual) == str(expected)
            if not matches:
                raise ZentaoError(
                    ErrorCode.CAPABILITY_UNAVAILABLE,
                    f"ZenTao accepted the request but {key} did not match the latest snapshot.",
                )
