from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import anyio
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from zentao_ai.cli.runtime import DependencyFactory

from .tools import TOOL_NAMES, ZentaoTools

logging.basicConfig(level=logging.WARNING)


async def execute_tool(
    tools: ZentaoTools, name: str, arguments: dict[str, Any]
) -> dict[str, Any] | types.CallToolResult:
    try:
        return tools.call(name, arguments)
    except Exception as exc:
        payload = {
            "version": "v1",
            "data": None,
            "error": {"type": type(exc).__name__, "message": "tool operation failed"},
        }
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="tool operation failed")],
            structuredContent=payload,
            isError=True,
        )


def create_server(tools: ZentaoTools) -> Server[object]:
    server: Server[object] = Server("zentao-ai", version="0.1.0")
    schemas = tools.schemas()

    @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_tools() -> list[types.Tool]:
        return [types.Tool(name=name, description=f"Zentao {name}", inputSchema=schemas[name]) for name in TOOL_NAMES]

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(
        name: str, arguments: dict[str, Any]
    ) -> dict[str, Any] | types.CallToolResult:
        return await execute_tool(tools, name, arguments)

    return server


async def _serve(project: Path, factory: DependencyFactory) -> None:
    with factory(project) as runtime:
        server = create_server(ZentaoTools(runtime))
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())


def serve(project: Path = Path.cwd(), factory: DependencyFactory | None = None) -> None:
    anyio.run(_serve, project.resolve(), factory or DependencyFactory())
