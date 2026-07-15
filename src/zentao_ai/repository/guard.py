from __future__ import annotations
import subprocess
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

ALLOWED_TEST_COMMANDS = frozenset({"pytest", "python -m pytest", "ruff check", "python -m ruff check", "mypy", "python -m mypy"})


class RepositoryMapping(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    repository: str
    path: Path
    targetBranch: str
    testCommands: tuple[str, ...] = ()


class GuardResult(BaseModel):
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    repository: str
    path: str
    branch: str | None = None
    head: str | None = None
    ahead: int | None = None
    behind: int | None = None
    testCommands: list[str] = Field(default_factory=list)


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, check=True, text=True, encoding="utf-8", errors="replace", capture_output=True).stdout.strip()


def preflight_repository(mapping: RepositoryMapping) -> GuardResult:
    reasons: list[str] = []
    path = mapping.path.resolve()
    try:
        top = Path(_git(path, "rev-parse", "--show-toplevel")).resolve()
        if top != path:
            reasons.append("REPOSITORY_PATH_NOT_TOP_LEVEL")
        head = _git(path, "rev-parse", "HEAD")
        branch = _git(path, "symbolic-ref", "--quiet", "--short", "HEAD")
        if branch != mapping.targetBranch:
            reasons.append("TARGET_BRANCH_MISMATCH")
        porcelain = _git(path, "status", "--porcelain=v1", "--untracked-files=all")
        if porcelain:
            reasons.append("WORKTREE_NOT_CLEAN")
        if any(line[:2].strip() for line in porcelain.splitlines() if line and line[:2] != "??"):
            reasons.append("STAGED_CHANGES_FORBIDDEN")
    except (OSError, subprocess.SubprocessError, ValueError):
        return GuardResult(allowed=False, reasons=["REPOSITORY_PREFLIGHT_FAILED"], repository=mapping.repository, path=str(path))
    ahead: int | None = None
    behind: int | None = None
    try:
        counts = _git(path, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
        ahead, behind = (int(value) for value in counts.split())
        if ahead or behind:
            reasons.append("UPSTREAM_DIVERGED")
    except (subprocess.SubprocessError, ValueError):
        reasons.append("UPSTREAM_REQUIRED")
    for command in mapping.testCommands:
        normalized = " ".join(command.split())
        if normalized not in ALLOWED_TEST_COMMANDS:
            reasons.append("TEST_COMMAND_NOT_ALLOWED")
    return GuardResult(allowed=not reasons, reasons=list(dict.fromkeys(reasons)), repository=mapping.repository, path=str(path), branch=branch, head=head, ahead=ahead, behind=behind, testCommands=list(mapping.testCommands))
