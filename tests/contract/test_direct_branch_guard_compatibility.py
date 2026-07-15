import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).parents[2] / "scripts" / "direct-branch-guard.py"
FIELDS = {"ok", "reasonCodes", "scopeName", "matchedRepositoryCount", "repositoryKey", "repositoryName", "repositoryPath", "upstream", "dirtyEntryCount"}


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
    return subprocess.run([sys.executable, str(SCRIPT), "preflight", "--config", str(config), "--scope-json", json.dumps(scope)], text=True, capture_output=True)


def test_golden_success_reads_config_and_selects_unique_repository(tmp_path: Path):
    repo, config = setup(tmp_path)
    result = run(config, {"product": " example site admin "})
    payload = json.loads(result.stdout)
    assert result.returncode == 0 and FIELDS <= payload.keys()
    assert payload | {"repositoryPath": str(repo.resolve())} == payload
    assert payload["ok"] and payload["matchedRepositoryCount"] == 1
    assert payload["upstream"] == "origin/main"
    assert payload["dirtyEntryCount"] == 0


def test_golden_no_match_and_invalid_config(tmp_path: Path):
    _, config = setup(tmp_path)
    result = run(config, {"product": "unknown"})
    assert result.returncode == 2 and json.loads(result.stdout)["reasonCodes"] == ["REPOSITORY_SCOPE_NO_MATCH"]
    invalid = run(tmp_path / "missing.yaml", {"product": "x"})
    assert invalid.returncode == 2 and json.loads(invalid.stdout)["reasonCodes"] == ["CONFIG_INVALID"]


def test_golden_ambiguous_scope_is_rejected(tmp_path: Path):
    _, config = setup(tmp_path)
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    data["personal"]["scopeNames"].append("Other")
    data["team"]["scopeNames"].append("Other")
    data["repositories"]["Other"] = {**data["repositories"]["Example Site Admin"], "repository": "other"}
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    result = run(config, {"product": "Example Site Admin", "project": "Other"})
    assert result.returncode == 2 and json.loads(result.stdout)["reasonCodes"] == ["REPOSITORY_SCOPE_AMBIGUOUS"]
