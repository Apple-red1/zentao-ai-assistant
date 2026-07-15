import subprocess
from pathlib import Path

from zentao_ai.repository import RepositoryMapping, preflight_repository, verify_repository_unchanged


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
    return repo


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


def test_dirty_staged_wrong_branch_and_unknown_test_fail_closed(tmp_path):
    repo = repository(tmp_path)
    (repo / "a.txt").write_text("dirty", encoding="utf-8")
    def mapping(branch="main", commands=("pytest",)):
        return RepositoryMapping(repository="example", path=repo, targetBranch=branch, testCommands=commands, configPath=tmp_path / "trusted.yaml", repositoryKey="scope")
    assert not preflight_repository(mapping()).allowed
    git(repo, "add", "a.txt")
    assert "STAGED_CHANGES_FORBIDDEN" in preflight_repository(mapping()).reasons
    git(repo, "reset", "--hard", "HEAD")
    git(repo, "checkout", "-b", "other")
    assert "TARGET_BRANCH_MISMATCH" in preflight_repository(mapping()).reasons
    git(repo, "checkout", "main")
    assert "TEST_COMMAND_NOT_ALLOWED" in preflight_repository(mapping(commands=("rm -rf .",))).reasons
