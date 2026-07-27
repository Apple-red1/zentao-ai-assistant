from __future__ import annotations

from typing import Any

from zentao_ai.models import Settings, ZentaoSettings
from zentao_ai.server import McpServices, ZentaoMcpServer

EXPECTED = {
    "query_my_bugs",
    "query_team_bugs",
    "query_user_bugs",
    "search_bugs",
    "get_bug",
    "list_users",
    "add_bug_comment",
    "edit_bug",
    "activate_bug",
    "assign_bug",
}


class Stub:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"Tool dependency should not be called while listing tools: {name}")


def server() -> ZentaoMcpServer:
    settings = Settings(
        version=1,
        zentao=ZentaoSettings(base_url="https://z.example", account="me"),
    )
    stub = Stub()
    return ZentaoMcpServer(
        McpServices(
            settings=settings,
            bugs=stub,  # type: ignore[arg-type]
            actions=stub,  # type: ignore[arg-type]
            users=stub,  # type: ignore[arg-type]
        )
    )


async def test_tool_inventory_has_no_delete_capability() -> None:
    names = set(await server().list_tool_names())

    assert names == EXPECTED
    assert not any("delete" in name or "remove" in name for name in names)


async def test_write_tool_schemas_require_literal_true_confirmation() -> None:
    tools = {tool.name: tool for tool in await server().mcp.list_tools()}

    for name in {"add_bug_comment", "edit_bug", "activate_bug", "assign_bug"}:
        confirm = tools[name].inputSchema["properties"]["confirm"]
        assert confirm.get("const") is True or confirm.get("enum") == [True]
        assert "bug_id" in tools[name].inputSchema["required"]
        assert "confirm" in tools[name].inputSchema["required"]
