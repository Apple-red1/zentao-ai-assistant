from __future__ import annotations

import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from zentao_ai.config import save_settings
from zentao_ai.models import Settings, ZentaoSettings


async def test_stdio_server_initializes_and_lists_tools(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    save_settings(
        Settings(
            version=1,
            zentao=ZentaoSettings(base_url="https://z.example", account="me"),
        ),
        config_path,
    )
    environment = dict(os.environ)
    environment["ZENTAO_CONFIG"] = str(config_path)
    environment["ZENTAO_PASSWORD"] = "example"
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "zentao_ai.cli", "mcp", "serve"],
        env=environment,
        cwd=Path(__file__).resolve().parents[2],
    )

    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()

    assert {tool.name for tool in tools.tools} == {
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
