from __future__ import annotations
import subprocess
import hashlib
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

class RepositoryMapping(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    repository: str
    path: Path
    targetBranch: str
    testCommands: tuple[str, ...] = ()
    configPath: Path
    repositoryKey: str


class GuardResult(BaseModel):
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    repository: str
    path: str
    branch: str | None = None
    head: str | None = None
    ahead: int | None = None
    behind: int | None = None
    upstream: str | None = None
    dirtyEntryCount: int = 0
    testCommands: list[str] = Field(default_factory=list)
    configPath: str | None = None
    repositoryKey: str | None = None
    indexFingerprint: str | None = None
    worktreeFingerprint: str | None = None
    preimageFingerprint: str | None = None


class RepositoryVerification(BaseModel):
    unchanged: bool
    reasons: list[str] = Field(default_factory=list)


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, check=True, text=True, encoding="utf-8", errors="replace", capture_output=True).stdout.rstrip("\r\n")


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
        if any(line[0] not in {" ", "?"} for line in porcelain.splitlines() if line):
            reasons.append("STAGED_CHANGES_FORBIDDEN")
    except (OSError, subprocess.SubprocessError, ValueError):
        return GuardResult(allowed=False, reasons=["REPOSITORY_PREFLIGHT_FAILED"], repository=mapping.repository, path=str(path), configPath=str(mapping.configPath.resolve()), repositoryKey=mapping.repositoryKey)
    ahead: int | None = None
    behind: int | None = None
    upstream: str | None = None
    try:
        upstream = _git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        counts = _git(path, "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
        ahead, behind = (int(value) for value in counts.split())
        if ahead or behind:
            reasons.append("UPSTREAM_DIVERGED")
    except (subprocess.SubprocessError, ValueError):
        reasons.append("UPSTREAM_REQUIRED")
    try:
        index_state = _git(path, "diff", "--cached", "--binary", "--no-ext-diff")
        worktree_state = _git(path, "status", "--porcelain=v1", "--untracked-files=all")
    except (OSError, subprocess.SubprocessError):
        return GuardResult(allowed=False, reasons=["REPOSITORY_PREFLIGHT_FAILED"], repository=mapping.repository, path=str(path), configPath=str(mapping.configPath.resolve()), repositoryKey=mapping.repositoryKey)
    preimage = f"{head}\0{branch}\0{index_state}\0{worktree_state}"
    return GuardResult(allowed=not reasons, reasons=list(dict.fromkeys(reasons)), repository=mapping.repository, path=str(path), branch=branch, head=head, ahead=ahead, behind=behind, upstream=upstream, dirtyEntryCount=len(worktree_state.splitlines()), testCommands=list(mapping.testCommands), configPath=str(mapping.configPath.resolve()), repositoryKey=mapping.repositoryKey, indexFingerprint=_fingerprint(index_state), worktreeFingerprint=_fingerprint(worktree_state), preimageFingerprint=_fingerprint(preimage))


def verify_repository_unchanged(lease: GuardResult) -> RepositoryVerification:
    reasons: list[str] = []
    if not lease.allowed or not lease.path:
        return RepositoryVerification(unchanged=False, reasons=["INVALID_REPOSITORY_LEASE"])
    path = Path(lease.path)
    try:
        head = _git(path, "rev-parse", "HEAD")
        branch = _git(path, "symbolic-ref", "--quiet", "--short", "HEAD")
        index_state = _git(path, "diff", "--cached", "--binary", "--no-ext-diff")
        worktree_state = _git(path, "status", "--porcelain=v1", "--untracked-files=all")
    except (OSError, subprocess.SubprocessError):
        return RepositoryVerification(unchanged=False, reasons=["REPOSITORY_RECHECK_FAILED"])
    if head != lease.head:
        reasons.append("HEAD_CHANGED")
    if branch != lease.branch:
        reasons.append("BRANCH_CHANGED")
    if _fingerprint(index_state) != lease.indexFingerprint:
        reasons.append("INDEX_CHANGED")
    if _fingerprint(worktree_state) != lease.worktreeFingerprint:
        reasons.append("WORKTREE_CHANGED")
    return RepositoryVerification(unchanged=not reasons, reasons=reasons)
