from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = ROOT / "plugins" / "zentao-ai-bug"


def test_manifest_wires_skill_and_mcp() -> None:
    manifest = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )

    assert manifest["name"] == "zentao-ai-bug"
    assert manifest["version"] == "0.1.0"
    assert manifest["author"]["name"] == "wwtweiwenting"
    assert manifest["repository"] == "https://github.com/wwtweiwenting/zentao-ai-assistant"
    assert manifest["license"] == "Apache-2.0"
    assert manifest["skills"] == "./skills/"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert manifest["interface"]["displayName"] == "禅道 AI Bug 助手"
    assert len(manifest["interface"]["defaultPrompt"]) <= 3


def test_mcp_uses_installed_cli() -> None:
    config = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server = config["mcpServers"]["zentao"]

    assert server == {"command": "zentao-ai", "args": ["mcp", "serve"], "cwd": "."}


def test_marketplace_points_to_plugin_with_install_policy() -> None:
    marketplace = json.loads(
        (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
    )
    entry = marketplace["plugins"][0]

    assert marketplace["name"] == "zentao-ai-assistant"
    assert entry["name"] == "zentao-ai-bug"
    assert entry["source"] == {"source": "local", "path": "./plugins/zentao-ai-bug"}
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}

