import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).parents[2] / "scripts" / "direct-branch-guard.py"
PROJECT_ROOT = SCRIPT.parents[1]
def git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


def setup(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", str(remote), str(repo)], check=True, capture_output=True)
    git(repo, "config", "user.email", "x@example.invalid")
    git(repo, "config", "user.name", "X")
    (repo / "a").write_text("a", encoding="utf-8")
    git(repo, "add", "a")
    git(repo, "commit", "-m", "x")
    git(repo, "branch", "-M", "main")
    git(repo, "push", "-u", "origin", "main")
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({"configVersion": 1, "personal": {"scopeNames": ["Example Site Admin"]}, "team": {"scopeNames": ["Example Site Admin"]}, "repositories": {"Example Site Admin": {"repository": "example-web", "path": str(repo), "targetBranch": "main", "testCommands": ["pytest"]}}}), encoding="utf-8")
    return repo, config


def run(config: Path, scope: object):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "preflight", "--config", str(config), "--scope-json", json.dumps(scope)],
        text=True,
        encoding="utf-8",
        capture_output=True,
    )


def test_golden_success_reads_config_and_selects_unique_repository(tmp_path: Path):
    repo, config = setup(tmp_path)
    result = run(config, {"product": " example site admin "})
    payload = json.loads(result.stdout)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True).stdout.strip()
    normalized = os.path.normcase(str(repo.resolve()))
    empty_hash = hashlib.sha256(b"").hexdigest()
    assert result.returncode == 0
    assert payload == {
        "ok": True, "reasonCodes": [], "scopeName": "example site admin", "matchedRepositoryCount": 1,
        "repositoryKey": hashlib.sha256(normalized.encode()).hexdigest(), "repositoryName": repo.name,
        "repositoryPath": str(repo.resolve()), "upstream": "origin/main", "dirtyEntryCount": 0,
        "ahead": 0, "behind": 0, "head": head, "branch": "main", "testCommands": ["pytest"],
        "indexFingerprint": empty_hash, "worktreeFingerprint": empty_hash,
        "preimageFingerprint": hashlib.sha256(f"{head}\0main\0\0".encode()).hexdigest(),
    }


def test_golden_no_match_and_invalid_config(tmp_path: Path):
    _, config = setup(tmp_path)
    result = run(config, {"product": "unknown"})
    assert result.returncode == 2 and json.loads(result.stdout)["reasonCodes"] == ["REPOSITORY_SCOPE_NO_MATCH"]
    invalid = run(tmp_path / "missing.yaml", {"product": "x"})
    assert invalid.returncode == 2 and json.loads(invalid.stdout)["reasonCodes"] == ["CONFIG_INVALID"]
    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("repositories: [unterminated", encoding="utf-8")
    broken = run(malformed, {"product": "x"})
    assert broken.returncode == 2
    assert broken.stderr == ""
    assert json.loads(broken.stdout)["reasonCodes"] == ["CONFIG_INVALID"]


def test_golden_ambiguous_scope_is_rejected(tmp_path: Path):
    _, config = setup(tmp_path)
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    data["personal"]["scopeNames"].append("Other")
    data["team"]["scopeNames"].append("Other")
    data["repositories"]["Other"] = {**data["repositories"]["Example Site Admin"], "repository": "other"}
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    result = run(config, {"product": "Example Site Admin", "project": "Other"})
    assert result.returncode == 2 and json.loads(result.stdout)["reasonCodes"] == ["REPOSITORY_SCOPE_AMBIGUOUS"]


def test_golden_malformed_scope_has_distinct_legacy_reason(tmp_path: Path):
    _, config = setup(tmp_path)
    for raw in ("{", "[]"):
        result = subprocess.run([sys.executable, str(SCRIPT), "preflight", "--config", str(config), "--scope-json", raw], text=True, capture_output=True)
        assert result.returncode == 2
        assert json.loads(result.stdout)["reasonCodes"] == ["SCOPE_JSON_INVALID"]


def test_non_ascii_uppercase_scope_uses_legacy_lower_matching(tmp_path: Path):
    repo, config = setup(tmp_path)
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    mapping = data["repositories"].pop("Example Site Admin")
    data["repositories"]["ÉΛΛΑ"] = mapping
    data["personal"]["scopeNames"] = ["ÉΛΛΑ"]
    data["team"]["scopeNames"] = ["ÉΛΛΑ"]
    config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    result = run(config, {"product": "éλλα"})
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["scopeName"] == "éλλα"
    assert payload["repositoryPath"] == str(repo.resolve())


def test_guard_entrypoints_write_utf8_json_with_non_utf8_stdio(tmp_path: Path):
    _, config = setup(tmp_path)
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    mapping = data["repositories"].pop("Example Site Admin")
    data["repositories"]["ÉQUIPE"] = mapping
    data["personal"]["scopeNames"] = ["ÉQUIPE"]
    data["team"]["scopeNames"] = ["ÉQUIPE"]
    config.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    env = {
        **os.environ,
        "PYTHONIOENCODING": "cp1252",
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
    }

    commands = (
        [sys.executable, str(SCRIPT)],
        [sys.executable, "-m", "zentao_ai.repository.cli"],
    )
    for command in commands:
        result = subprocess.run(
            [
                *command,
                "preflight",
                "--config",
                str(config),
                "--scope-json",
                json.dumps({"product": "équipe"}),
            ],
            capture_output=True,
            env=env,
        )

        payload = json.loads(result.stdout.decode("utf-8"))
        assert result.returncode == 0
        assert payload["scopeName"] == "équipe"
