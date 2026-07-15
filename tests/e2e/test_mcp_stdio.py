from __future__ import annotations

import json
import os
import subprocess
import sys


def send(process: subprocess.Popen[str], payload: dict[str, object]) -> dict[str, object]:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())


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
        [sys.executable, "-m", "zentao_ai.cli.app", "mcp", "serve", "--project", str(tmp_path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", env=env,
    )
    initialized = send(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}})
    assert initialized["id"] == 1 and "result" in initialized
    assert process.stdin is not None
    process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")
    process.stdin.flush()
    listed = send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert {tool["name"] for tool in listed["result"]["tools"]} >= {"query_bug_detail", "add_bug_comment"}
    response = send(process, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "query_bug_detail", "arguments": {"bugId": 7, "unknown": 1}}})
    assert response["result"]["isError"] is True
    process.stdin.close()
    assert process.wait(timeout=10) == 0
