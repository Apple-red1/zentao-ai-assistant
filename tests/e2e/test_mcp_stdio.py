from __future__ import annotations

import json
import os
import subprocess
import sys

from zentao_ai.mcp_server.tools import TOOL_NAMES


def send(
    process: subprocess.Popen[str], payload: dict[str, object], frames: list[str]
) -> dict[str, object]:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()
    frame = process.stdout.readline().strip()
    frames.append(frame)
    return json.loads(frame)


def test_stdio_initialize_list_and_shutdown_frames_are_stdout_pure(tmp_path) -> None:
    config = tmp_path / ".codex" / "zentao-ai-bug.yaml"
    config.parent.mkdir()
    config.write_text(
        "configVersion: 1\nzentao: {baseUrl: 'https://zentao.example', account: alice}\n"
        "personal: {scopeNames: [demo]}\nteam: {scopeNames: [demo], members: [alice]}\n"
        "repositories: {demo: {repository: demo, path: '.', targetBranch: main, testCommands: [pytest]}}\n",
        encoding="utf-8",
    )
    env = dict(os.environ, ZENTAO_API_TOKEN="fake-only-for-construction")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "zentao_ai.cli.app",
            "mcp",
            "serve",
            "--project",
            str(tmp_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )
    frames: list[str] = []
    initialized = send(
        process,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        },
        frames,
    )
    assert initialized["id"] == 1 and "result" in initialized
    assert process.stdin is not None
    process.stdin.write(
        json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        )
        + "\n"
    )
    process.stdin.flush()
    listed = send(
        process,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        frames,
    )
    assert tuple(tool["name"] for tool in listed["result"]["tools"]) == TOOL_NAMES
    response = send(
        process,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "query_bug_detail",
                "arguments": {"bugId": 7, "unknown": 1},
            },
        },
        frames,
    )
    assert response["result"]["isError"] is True
    # MCP SDK 1.x exposes no ShutdownRequest type/handler. Send the JSON-RPC
    # lifecycle notification, then EOF, which is the SDK's supported stop signal.
    process.stdin.write(
        json.dumps({"jsonrpc": "2.0", "method": "shutdown", "params": {}}) + "\n"
    )
    process.stdin.flush()
    process.stdin.close()
    assert process.wait(timeout=10) == 0
    assert process.stdout.read() == ""
    decoded = [json.loads(frame) for frame in frames]
    assert all(frame["jsonrpc"] == "2.0" for frame in decoded)
    assert [frame["id"] for frame in decoded] == [1, 2, 3]
