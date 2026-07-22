import subprocess
from pathlib import Path
import pytest
import yaml

from zentao_ai.repository import RepositoryMapping, preflight_repository, verify_repository_unchanged
from zentao_ai.repository import guard


def git(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, check=True, text=True, capture_output=True).stdout.strip()


def repository(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", str(remote), str(repo)], check=True, capture_output=True)
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    (repo / "a.txt").write_text("a", encoding="utf-8")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-m", "initial")
    git(repo, "branch", "-M", "main")
    git(repo, "push", "-u", "origin", "main")
    write_config(tmp_path / "trusted.yaml", repo)
    return repo


def write_config(path: Path, repo: Path, commands=("pytest",)) -> None:
    data = {"configVersion": 1, "personal": {"scopeNames": ["scope"]}, "team": {"scopeNames": ["scope"]}, "repositories": {"scope": {"repository": "example", "path": str(repo), "targetBranch": "main", "testCommands": list(commands)}}}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def mapping(tmp_path: Path, repo: Path, target_branch="main", commands=("pytest",)) -> RepositoryMapping:
    return RepositoryMapping(repository="example", path=repo, targetBranch=target_branch, testCommands=commands, configPath=tmp_path / "trusted.yaml", repositoryKey="scope")


def test_clean_exact_repository_passes_without_changing_head(tmp_path):
    repo = repository(tmp_path)
    before = git(repo, "rev-parse", "HEAD")
    result = preflight_repository(RepositoryMapping(repository="example", path=repo, targetBranch="main", testCommands=("pytest",), configPath=tmp_path / "trusted.yaml", repositoryKey="scope"))
    assert result.allowed and result.ahead == result.behind == 0
    assert result.head == before == git(repo, "rev-parse", "HEAD")
    assert result.indexFingerprint and result.worktreeFingerprint and result.preimageFingerprint
    assert verify_repository_unchanged(result).unchanged
    (repo / "new.txt").write_text("changed", encoding="utf-8")
    changed = verify_repository_unchanged(result)
    assert not changed.unchanged and "WORKTREE_CHANGED" in changed.reasons


def test_dirty_staged_and_unknown_test_fail_closed(tmp_path):
    repo = repository(tmp_path)
    (repo / "a.txt").write_text("dirty", encoding="utf-8")
    def trusted_mapping(branch="main", commands=("pytest",)):
        return RepositoryMapping(repository="example", path=repo, targetBranch=branch, testCommands=commands, configPath=tmp_path / "trusted.yaml", repositoryKey="scope")
    dirty = preflight_repository(trusted_mapping())
    assert not dirty.allowed
    assert "STAGED_CHANGES_FORBIDDEN" not in dirty.reasons
    git(repo, "add", "a.txt")
    assert "STAGED_CHANGES_FORBIDDEN" in preflight_repository(trusted_mapping()).reasons
    git(repo, "reset", "--hard", "HEAD")
    git(repo, "checkout", "-b", "other")
    git(repo, "push", "-u", "origin", "other")
    other = preflight_repository(trusted_mapping())
    assert other.allowed
    assert "TARGET_BRANCH_MISMATCH" not in other.reasons
    git(repo, "checkout", "main")
    write_config(tmp_path / "trusted.yaml", repo, ("custom-safe-test --flag",))
    assert "TEST_COMMAND_NOT_ALLOWED" not in preflight_repository(trusted_mapping(commands=("custom-safe-test --flag",))).reasons


@pytest.mark.parametrize("branch", ["dev", "development-x", "DEV-fix", "test", "test_fix", "release", "release/1.0"])
def test_forbidden_branch_prefixes_fail_closed(tmp_path, branch):
    repo = repository(tmp_path)
    git(repo, "checkout", "-b", branch)
    git(repo, "push", "-u", "origin", branch)
    result = preflight_repository(mapping(tmp_path, repo))
    assert not result.allowed
    assert "PROTECTED_BRANCH" in result.reasons
    assert "TARGET_BRANCH_MISMATCH" not in result.reasons


@pytest.mark.parametrize("branch", ["main", "master"])
def test_exact_main_and_master_are_forbidden(tmp_path, branch):
    repo = repository(tmp_path)
    if branch != "main":
        git(repo, "checkout", "-b", branch)
        git(repo, "push", "-u", "origin", branch)
    result = preflight_repository(mapping(tmp_path, repo))
    assert not result.allowed
    assert "PROTECTED_BRANCH" in result.reasons


@pytest.mark.parametrize("branch", ["MAIN", "Master", "Development-X", "TEST_fix", "Release/1.0"])
def test_protected_branch_policy_is_case_insensitive(branch):
    assert guard._is_protected_branch(branch)


@pytest.mark.parametrize("branch", ["0720-temp", "wwt_play", "feature/main-fix"])
def test_other_synchronized_branches_do_not_require_target_branch_match(tmp_path, branch):
    repo = repository(tmp_path)
    git(repo, "checkout", "-b", branch)
    git(repo, "push", "-u", "origin", branch)
    result = preflight_repository(mapping(tmp_path, repo))
    assert result.allowed
    assert "TARGET_BRANCH_MISMATCH" not in result.reasons


def test_forged_mapping_is_rejected_against_trusted_config(tmp_path):
    repo = repository(tmp_path)
    forged = RepositoryMapping(repository="example", path=repo, targetBranch="other", testCommands=("pytest",), configPath=tmp_path / "trusted.yaml", repositoryKey="scope")
    result = preflight_repository(forged)
    assert not result.allowed and result.reasons == ["REPOSITORY_PROVENANCE_INVALID"]


def test_malformed_trusted_yaml_is_provenance_denial_without_exception(tmp_path):
    repo = repository(tmp_path)
    config = tmp_path / "trusted.yaml"
    config.write_text("repositories: [unterminated", encoding="utf-8")
    mapping = RepositoryMapping(repository="example", path=repo, targetBranch="main", testCommands=("pytest",), configPath=config, repositoryKey="scope")
    result = preflight_repository(mapping)
    assert not result.allowed and result.reasons == ["REPOSITORY_PROVENANCE_INVALID"]


def test_repository_disappearing_during_final_fingerprint_is_denied(tmp_path, monkeypatch):
    repo = repository(tmp_path)
    from zentao_ai.repository import guard
    original = guard._git
    calls = 0

    def disappearing(path, *args):
        nonlocal calls
        calls += 1
        if calls > 7:
            raise OSError("gone")
        return original(path, *args)

    monkeypatch.setattr(guard, "_git", disappearing)
    mapping = RepositoryMapping(repository="example", path=repo, targetBranch="main", testCommands=("pytest",), configPath=tmp_path / "trusted.yaml", repositoryKey="scope")
    result = preflight_repository(mapping)
    assert not result.allowed and "REPOSITORY_PREFLIGHT_FAILED" in result.reasons


def test_upstream_reads_catch_oserror_at_calls_five_and_six(tmp_path, monkeypatch):
    from zentao_ai.repository import guard
    for failing_call in (5, 6):
        repo = repository(tmp_path / str(failing_call))
        original = guard._git
        calls = 0
        def fail(path, *args):
            nonlocal calls
            calls += 1
            if calls == failing_call:
                raise OSError("gone")
            return original(path, *args)
        monkeypatch.setattr(guard, "_git", fail)
        mapping = RepositoryMapping(repository="example", path=repo, targetBranch="main", testCommands=("pytest",), configPath=tmp_path / str(failing_call) / "trusted.yaml", repositoryKey="scope")
        assert not preflight_repository(mapping).allowed
        monkeypatch.setattr(guard, "_git", original)
