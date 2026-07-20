from __future__ import annotations

import json
import marshal
import re
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "zentao-ai-bug"
UNPUBLISHED_PYPI_INSTALL = bytes(
    [112, 105, 112, 120, 32, 105, 110, 115, 116, 97, 108, 108, 32]
    + [122, 101, 110, 116, 97, 111, 45, 97, 105, 45, 97, 115, 115, 105, 115, 116, 97, 110, 116]
).decode("ascii")
TEXT_SUFFIXES = {".json", ".md", ".py", ".rst", ".toml", ".txt", ".yaml", ".yml"}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_package_exposes_plugin_companion_commands() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = project["project"]["scripts"]
    assert scripts["zentao-ai"] == "zentao_ai.cli.app:main"
    assert scripts["zentao-ai-state"] == "zentao_ai.state.cli:main"
    assert scripts["zentao-ai-repository"] == "zentao_ai.repository.cli:main"
    assert scripts["zentao-ai-render-report"] == "zentao_ai.reporting.cli:main"


def test_manifest_is_complete_and_references_real_components() -> None:
    manifest = load_json(PLUGIN / ".codex-plugin" / "plugin.json")
    assert manifest["name"] == "zentao-ai-bug"
    assert manifest["version"] == "0.1.0"
    assert manifest["license"] == "Apache-2.0"
    assert manifest["author"] == {"name": "Zentao AI Assistant contributors"}
    assert manifest["repository"] == "https://github.com/wwtweiwenting/zentao-ai-assistant"
    assert manifest["homepage"] == "https://github.com/wwtweiwenting/zentao-ai-assistant"
    assert manifest["skills"] == "./skills/"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert set(manifest["interface"]["capabilities"]) == {"Read", "Interactive", "Write"}
    assert 1 <= len(manifest["interface"]["defaultPrompt"]) <= 3
    assert not ({"assets", "apps", "hooks"} & set(manifest))
    for field in ("skills", "mcpServers"):
        assert (PLUGIN / manifest[field]).exists()


def test_mcp_config_registers_only_installed_cli_without_secrets() -> None:
    config = load_json(PLUGIN / ".mcp.json")
    assert list(config["mcpServers"]) == ["zentao"]
    server = config["mcpServers"]["zentao"]
    assert server["type"] == "stdio"
    assert server["command"] == "zentao-ai"
    assert server["args"] == ["mcp", "serve"]
    assert server["env"] == {"ZENTAO_AI_CONFIG": "${ZENTAO_AI_CONFIG}"}
    text = json.dumps(config).lower()
    assert not re.search(r"(password|token|cookie|secret)\s*[\"']?\s*[:=]", text)


def test_cli_and_configured_mcp_backend_are_importable_smoke() -> None:
    env = {**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")}
    for arguments in (["--help"], ["mcp", "--help"]):
        result = subprocess.run(
            [sys.executable, "-m", "zentao_ai.cli.app", *arguments],
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        assert result.returncode == 0, result.stderr
    import_result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from zentao_ai.mcp_server.server import serve; "
            "from zentao_ai.mcp_server.tools import TOOL_NAMES; "
            "assert serve and TOOL_NAMES",
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert import_result.returncode == 0, import_result.stderr


def test_marketplace_entry_is_team_installable() -> None:
    market = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert market["name"] == "zentao-team"
    assert market["interface"] == {"displayName": "Zentao Team"}
    entry = next(item for item in market["plugins"] if item["name"] == "zentao-ai-bug")
    assert entry["source"] == {"source": "local", "path": "./plugins/zentao-ai-bug"}
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert entry["category"] == "Productivity"


def test_github_marketplace_keeps_repository_relative_plugin_path() -> None:
    text = (ROOT / "docs" / "plugin-installation.md").read_text(encoding="utf-8")
    assert "wwtweiwenting/zentao-ai-assistant@feature/zentao-open-source" in text
    market = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    entry = next(item for item in market["plugins"] if item["name"] == "zentao-ai-bug")
    assert entry["source"] == {"source": "local", "path": "./plugins/zentao-ai-bug"}


def test_plugin_wrappers_are_standard_library_dispatchers() -> None:
    expected = {
        "run-ledger.py": ("zentao-ai-state",),
        "direct-branch-guard.py": ("zentao-ai-repository",),
        "render-report.py": ("zentao-ai-render-report",),
        "doctor.py": ("zentao-ai", "doctor"),
    }
    for filename, command in expected.items():
        path = PLUGIN / "scripts" / filename
        text = path.read_text(encoding="utf-8")
        assert "zentao_ai" not in text
        assert "sys.path" not in text
        assert "shutil.which" in text
        assert "subprocess.call" in text
        probe = f'''import json, runpy, shutil, subprocess, sys
seen = {{}}
def which(name):
    seen["which"] = name
    return "C:/fake/" + name + ".exe"
def call(argv):
    seen["argv"] = argv
    return 23
shutil.which = which
subprocess.call = call
sys.argv = [{str(path)!r}, "alpha", "beta"]
try:
    runpy.run_path({str(path)!r}, run_name="__main__")
except SystemExit as exc:
    seen["exit"] = exc.code
print(json.dumps(seen))
'''
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-c", probe],
            text=True,
            capture_output=True,
            check=False,
            env={**__import__("os").environ, "PATH": ""},
        )
        assert result.returncode == 0, result.stderr
        seen = json.loads(result.stdout)
        executable = f"C:/fake/{command[0]}.exe"
        assert seen == {
            "which": command[0],
            "argv": [executable, *command[1:], "alpha", "beta"],
            "exit": 23,
        }

    index = subprocess.run(
        ["git", "ls-files", "--stage", "plugins/zentao-ai-bug/scripts"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    assert len(index) == len(expected)
    assert all(line.startswith("100755 ") for line in index)


def test_repository_guard_has_an_installed_cli_entrypoint() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "zentao_ai.repository.cli", "--help"],
        text=True,
        capture_output=True,
        check=False,
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
    )
    assert result.returncode == 0, result.stderr
    assert "preflight" in result.stdout


def test_wrappers_report_github_install_error_when_package_is_unavailable() -> None:
    github_install = (
        'pipx install "git+https://github.com/wwtweiwenting/'
        'zentao-ai-assistant.git@feature/zentao-open-source"'
    )
    for wrapper in (PLUGIN / "scripts").glob("*.py"):
        isolated = subprocess.run(
            [sys.executable, "-I", "-S", str(wrapper), "--help"],
            text=True,
            capture_output=True,
            check=False,
            env={**__import__("os").environ, "PATH": ""},
        )
        assert isolated.returncode != 0
        assert github_install in isolated.stderr
        assert "pipx install ." not in isolated.stderr


def test_plugin_and_all_docs_never_claim_an_unpublished_pypi_install() -> None:
    files = [
        path
        for root in (PLUGIN, ROOT / "docs")
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES
    ]
    for path in files:
        assert UNPUBLISHED_PYPI_INSTALL not in path.read_text(encoding="utf-8")


def test_forbidden_install_command_is_not_embedded_in_compiled_test_bytecode() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    bytecode = marshal.dumps(compile(source, __file__, "exec"))
    needle = bytes(
        [112, 105, 112, 120, 32, 105, 110, 115, 116, 97, 108, 108, 32]
        + [122, 101, 110, 116, 97, 111, 45, 97, 105, 45, 97, 115, 115, 105, 115, 116, 97, 110, 116]
    )
    assert needle not in bytecode


def test_installation_document_covers_supported_plugin_flow() -> None:
    text = (ROOT / "docs" / "plugin-installation.md").read_text(encoding="utf-8")
    github_cli = (
        'pipx install "git+https://github.com/wwtweiwenting/'
        'zentao-ai-assistant.git@feature/zentao-open-source"'
    )
    github_marketplace = (
        'codex plugin marketplace add '
        '"wwtweiwenting/zentao-ai-assistant@feature/zentao-open-source"'
    )
    assert github_cli in text
    assert github_marketplace in text
    assert "pipx install ." not in text
    assert "codex plugin marketplace add ." not in text
    for required in (
        "zentao-team",
        "Codex app",
        "Windows",
        "macOS",
        "Linux",
        "new task",
    ):
        assert required in text
    assert "codex plugin add" not in text
    assert UNPUBLISHED_PYPI_INSTALL not in text
    assert "尚未发布到 PyPI" in text
    assert "私有仓库" in text
    assert "读取权限" in text
    assert "已认证凭据" in text
    assert not re.search(r"(?i)(password|token|cookie|secret)\s*[:=]\s*\S+", text)


def test_package_contains_no_placeholder_or_destructive_tool_registration() -> None:
    package_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in PLUGIN.rglob("*")
        if path.is_file()
    )
    assert "[TODO:" not in package_text
    assert "Local developer" not in package_text
    mcp_allowlists = re.findall(r"^- `([^`]+)`", package_text, flags=re.MULTILINE)
    assert "delete_bug" not in mcp_allowlists
    assert "remove_bug" not in mcp_allowlists
