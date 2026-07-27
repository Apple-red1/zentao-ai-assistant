from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ValidationError

from zentao_ai.actions import BugActionService
from zentao_ai.bugs import BugService
from zentao_ai.errors import ErrorCode, ZentaoError
from zentao_ai.models import BugChanges, BugFilters, Settings, WriteAuthorization
from zentao_ai.users import UserDirectory, UserKind

T = TypeVar("T")


@dataclass(frozen=True)
class McpServices:
    settings: Settings
    bugs: BugService
    actions: BugActionService
    users: UserDirectory


class ZentaoMcpServer:
    def __init__(self, services: McpServices) -> None:
        self._services = services
        self.mcp = FastMCP(
            "zentao-ai-bug",
            instructions=(
                "Query and update ZenTao 21.7.8 Bugs. Write tools require the current user "
                "message to explicitly identify the Bug, action, and arguments."
            ),
        )
        self._register_tools()

    async def list_tool_names(self) -> list[str]:
        return sorted(tool.name for tool in await self.mcp.list_tools())

    def run_stdio(self) -> None:
        self.mcp.run(transport="stdio")

    def _register_tools(self) -> None:
        services = self._services

        @self.mcp.tool(
            description="查询本地配置账号当前未关闭或指定条件的 Bug，并返回汇总。"
        )
        async def query_my_bugs(filters: BugFilters | None = None) -> dict[str, Any]:
            return await _safe(services.bugs.query_my_bugs(filters))

        @self.mcp.tool(description="查询本地配置的团队成员 Bug；单个成员失败时返回部分结果。")
        async def query_team_bugs(filters: BugFilters | None = None) -> dict[str, Any]:
            try:
                validation = await services.users.validate_team(services.settings.team.members)
                result = await services.bugs.query_team_bugs(validation.resolved, filters)
                config_failures = [
                    {
                        "account": failure.account,
                        "code": failure.code,
                        "message": failure.reason,
                    }
                    for failure in validation.failures
                ]
                if config_failures:
                    result = result.model_copy(
                        update={
                            "partial_failures": [
                                *result.partial_failures,
                                *config_failures,
                            ]
                        }
                    )
                return _ok(result)
            except (ZentaoError, ValidationError) as exc:
                return _error(exc)
            except Exception:
                return _unexpected_error()

        @self.mcp.tool(description="按账号或姓名查询内部或外部人员的 Bug。")
        async def query_user_bugs(
            user: str,
            kind: UserKind = "all",
            filters: BugFilters | None = None,
        ) -> dict[str, Any]:
            try:
                resolved = await services.users.resolve(user, kind=kind)
                return _ok(await services.bugs.query_user_bugs(resolved, filters))
            except (ZentaoError, ValidationError) as exc:
                return _error(exc)
            except Exception:
                return _unexpected_error()

        @self.mcp.tool(
            description="按产品、项目、执行、状态、人员、等级、日期或关键词组合查询 Bug。"
        )
        async def search_bugs(filters: BugFilters | None = None) -> dict[str, Any]:
            return await _safe(services.bugs.search_bugs(filters))

        @self.mcp.tool(description="读取单个 Bug 的最新详情。")
        async def get_bug(bug_id: int) -> dict[str, Any]:
            return await _safe(services.bugs.get_bug(bug_id))

        @self.mcp.tool(description="列出禅道内部人员、外部人员或全部人员。")
        async def list_users(kind: UserKind = "all") -> dict[str, Any]:
            return await _safe(services.users.list_users(kind))

        @self.mcp.tool(
            description=(
                "为指定 Bug 添加备注。只有当前用户消息明确要求该 Bug 和备注时，"
                "调用方才能把 confirm 设为 true。"
            )
        )
        async def add_bug_comment(
            bug_id: int,
            comment: str,
            confirm: Literal[True],
        ) -> dict[str, Any]:
            authorization = WriteAuthorization(
                confirm=confirm,
                bug_id=bug_id,
                action="comment",
            )
            return await _safe(services.actions.add_comment(bug_id, comment, authorization))

        @self.mcp.tool(
            description=(
                "编辑指定 Bug 的白名单字段。只有当前用户消息明确要求这些修改时，"
                "调用方才能把 confirm 设为 true。"
            )
        )
        async def edit_bug(
            bug_id: int,
            changes: BugChanges,
            confirm: Literal[True],
        ) -> dict[str, Any]:
            authorization = WriteAuthorization(
                confirm=confirm,
                bug_id=bug_id,
                action="edit",
            )
            return await _safe(services.actions.edit_bug(bug_id, changes, authorization))

        @self.mcp.tool(
            description=(
                "激活已解决或已关闭的 Bug。只有当前用户消息明确要求该动作时，"
                "调用方才能把 confirm 设为 true。"
            )
        )
        async def activate_bug(
            bug_id: int,
            opened_builds: list[str],
            confirm: Literal[True],
            assigned_to: str | None = None,
            comment: str | None = None,
        ) -> dict[str, Any]:
            authorization = WriteAuthorization(
                confirm=confirm,
                bug_id=bug_id,
                action="activate",
            )
            return await _safe(
                services.actions.activate_bug(
                    bug_id,
                    opened_builds,
                    authorization,
                    assigned_to=assigned_to,
                    comment=comment,
                )
            )

        @self.mcp.tool(
            description=(
                "把指定 Bug 指派给账号或姓名。只有当前用户消息明确要求该动作时，"
                "调用方才能把 confirm 设为 true。"
            )
        )
        async def assign_bug(
            bug_id: int,
            assigned_to: str,
            confirm: Literal[True],
            comment: str | None = None,
        ) -> dict[str, Any]:
            authorization = WriteAuthorization(
                confirm=confirm,
                bug_id=bug_id,
                action="assign",
            )
            return await _safe(
                services.actions.assign_bug(
                    bug_id,
                    assigned_to,
                    comment,
                    authorization,
                )
            )


async def _safe(awaitable: Awaitable[T]) -> dict[str, Any]:
    try:
        return _ok(await awaitable)
    except (ZentaoError, ValidationError) as exc:
        return _error(exc)
    except Exception:
        return _unexpected_error()


def _ok(value: object) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        data: object = value.model_dump(mode="json")
    elif isinstance(value, list):
        data = [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item
            for item in value
        ]
    else:
        data = value
    return {"ok": True, "data": data}


def _error(exc: ZentaoError | ValidationError) -> dict[str, Any]:
    if isinstance(exc, ZentaoError):
        return exc.to_dict()
    return ZentaoError(
        ErrorCode.VALIDATION_ERROR,
        "Tool arguments did not pass validation.",
    ).to_dict()


def _unexpected_error() -> dict[str, Any]:
    return ZentaoError(
        ErrorCode.CAPABILITY_UNAVAILABLE,
        "The ZenTao plugin encountered an unexpected local error.",
    ).to_dict()
