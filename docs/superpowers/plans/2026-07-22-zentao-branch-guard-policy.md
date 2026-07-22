# Zentao Branch Guard Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make repository preflight ignore `targetBranch` for branch authorization while rejecting branches that start with `dev`, `test`, or `release`, plus exact `main` and `master`, case-insensitively.

**Architecture:** Keep `targetBranch` in `RepositoryMapping` and trusted-config provenance checks for backward-compatible configuration identity, but move authorization to a small pure branch-name predicate in `repository/guard.py`. Update the plugin contract so runtime documentation and executable behavior share one policy.

**Tech Stack:** Python 3.12, Pydantic, pytest, Git CLI, Markdown contract tests.

## Global Constraints

- Branch comparisons are case-insensitive.
- Reject prefixes `dev`, `test`, and `release`.
- Reject exact names `main` and `master`.
- Do not use `targetBranch` to authorize or reject the current branch.
- Preserve all existing repository provenance, cleanliness, upstream, synchronization, and fingerprint checks.
- Keep the `targetBranch` configuration field for compatibility.

---

### Task 1: Lock the Branch Policy with Regression Tests

**Files:**
- Modify: `tests/unit/repository/test_guard.py`

**Interfaces:**
- Consumes: `preflight_repository(mapping: RepositoryMapping) -> GuardResult`
- Produces: regression coverage for allowed and forbidden branch names independent of `targetBranch`

- [ ] **Step 1: Replace the obsolete wrong-target assertion with parameterized policy tests**

Add tests that create synchronized remote-tracking branches and assert:

```python
@pytest.mark.parametrize("branch", ["dev", "development-x", "DEV-fix", "test", "test_fix", "release", "release/1.0"])
def test_forbidden_branch_prefixes_fail_closed(tmp_path, branch):
    repo = repository(tmp_path)
    git(repo, "checkout", "-b", branch)
    git(repo, "push", "-u", "origin", branch)
    result = preflight_repository(
        RepositoryMapping(
            repository="example",
            path=repo,
            targetBranch="main",
            testCommands=("pytest",),
            configPath=tmp_path / "trusted.yaml",
            repositoryKey="scope",
        )
    )
    assert not result.allowed
    assert "PROTECTED_BRANCH" in result.reasons
    assert "TARGET_BRANCH_MISMATCH" not in result.reasons


@pytest.mark.parametrize("branch", ["main", "master", "MAIN", "Master"])
def test_exact_main_and_master_are_forbidden(tmp_path, branch):
    repo = repository(tmp_path)
    if branch != "main":
        git(repo, "checkout", "-b", branch)
        git(repo, "push", "-u", "origin", branch)
    result = preflight_repository(
        RepositoryMapping(
            repository="example",
            path=repo,
            targetBranch="main",
            testCommands=("pytest",),
            configPath=tmp_path / "trusted.yaml",
            repositoryKey="scope",
        )
    )
    assert not result.allowed
    assert "PROTECTED_BRANCH" in result.reasons


@pytest.mark.parametrize("branch", ["0720-temp", "wwt_play", "feature/main-fix"])
def test_other_synchronized_branches_do_not_require_target_branch_match(tmp_path, branch):
    repo = repository(tmp_path)
    git(repo, "checkout", "-b", branch)
    git(repo, "push", "-u", "origin", branch)
    result = preflight_repository(
        RepositoryMapping(
            repository="example",
            path=repo,
            targetBranch="main",
            testCommands=("pytest",),
            configPath=tmp_path / "trusted.yaml",
            repositoryKey="scope",
        )
    )
    assert result.allowed
    assert "TARGET_BRANCH_MISMATCH" not in result.reasons
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m pytest tests/unit/repository/test_guard.py -q
```

Expected: failures show `TARGET_BRANCH_MISMATCH` is still emitted and `PROTECTED_BRANCH` is absent.

- [ ] **Step 3: Commit only the failing tests after confirming the expected failure**

```powershell
git add tests/unit/repository/test_guard.py
git commit -m "test: define branch guard policy"
```

### Task 2: Implement the Minimal Branch Predicate

**Files:**
- Modify: `src/zentao_ai/repository/guard.py`

**Interfaces:**
- Produces: `_is_protected_branch(branch: str) -> bool`
- Consumes: branch returned by `git symbolic-ref --short HEAD`

- [ ] **Step 1: Add the pure predicate**

```python
def _is_protected_branch(branch: str) -> bool:
    normalized = branch.casefold()
    return normalized in {"main", "master"} or normalized.startswith(("dev", "test", "release"))
```

- [ ] **Step 2: Replace target-branch authorization**

Replace:

```python
if branch != mapping.targetBranch:
    reasons.append("TARGET_BRANCH_MISMATCH")
```

with:

```python
if _is_protected_branch(branch):
    reasons.append("PROTECTED_BRANCH")
```

- [ ] **Step 3: Run the focused tests and verify GREEN**

Run:

```powershell
python -m pytest tests/unit/repository/test_guard.py -q
```

Expected: all repository guard unit tests pass.

- [ ] **Step 4: Commit the implementation**

```powershell
git add src/zentao_ai/repository/guard.py
git commit -m "fix: enforce protected branch prefixes"
```

### Task 3: Align Plugin Contracts and Documentation

**Files:**
- Modify: `plugins/zentao-ai-bug/skills/zentao-ai-bug/SKILL.md`
- Modify: `plugins/zentao-ai-bug/skills/zentao-ai-bug/personal-bug-agent.md`
- Modify: `plugins/zentao-ai-bug/skills/zentao-ai-bug/bug-analysis.md`
- Modify: `tests/contract/test_legacy_feature_inventory.py`

**Interfaces:**
- Produces: one visible policy shared by skill instructions and contract tests

- [ ] **Step 1: Update the contract test before documentation**

Change the branch-gate evidence phrases to require:

```python
"分支门禁": (
    "personal-bug-agent.md",
    ("以 `dev`、`test` 或 `release` 开头", "精确等于 `main` 或 `master`", "ahead/behind 为 `0/0`", "不执行 checkout"),
),
```

- [ ] **Step 2: Run the contract test and verify RED**

Run:

```powershell
python -m pytest tests/contract/test_legacy_feature_inventory.py -q
```

Expected: failure because the new policy phrases are not yet in `personal-bug-agent.md`.

- [ ] **Step 3: Update all three skill documents**

State consistently that `targetBranch` is compatibility metadata, prefix rules apply to `dev/test/release`, exact rules apply to `main/master`, comparisons are case-insensitive, and `feature/main-fix` remains allowed.

- [ ] **Step 4: Run contract and skill tests**

Run:

```powershell
python -m pytest tests/contract/test_legacy_feature_inventory.py tests/test_skill_contract.py tests/test_zentao_skill_contract.py -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit documentation and contract changes**

```powershell
git add plugins/zentao-ai-bug/skills/zentao-ai-bug/SKILL.md plugins/zentao-ai-bug/skills/zentao-ai-bug/personal-bug-agent.md plugins/zentao-ai-bug/skills/zentao-ai-bug/bug-analysis.md tests/contract/test_legacy_feature_inventory.py
git commit -m "docs: align branch guard contract"
```

### Task 4: Verify, Publish, Reinstall, and Smoke-Test

**Files:**
- Verify only: repository-wide source and tests
- Install from: `git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source`

**Interfaces:**
- Produces: pushed branch and locally installed CLI/plugin using the same revision

- [ ] **Step 1: Run the full test suite**

```powershell
python -m pytest -q
```

Expected: zero failures.

- [ ] **Step 2: Inspect scope and history**

```powershell
git diff --check origin/feature/zentao-open-source...HEAD
git status -sb
git log --oneline origin/feature/zentao-open-source..HEAD
```

Expected: only the pre-existing routing commit plus approved design, tests, implementation, and contract commits; working tree clean.

- [ ] **Step 3: Push the approved current branch**

```powershell
git push origin feature/zentao-open-source
```

Expected: remote branch advances to local HEAD.

- [ ] **Step 4: Reinstall the CLI from the pushed branch**

```powershell
pipx install --force "git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source"
```

Expected: `zentao-ai-assistant` reinstalls successfully and exposes `zentao-ai-repository`, `zentao-ai-state`, and `zentao-ai-render-report`.

- [ ] **Step 5: Refresh the Codex plugin cache using the repository's documented installation command**

Follow `docs/plugin-installation.md` exactly for the current Codex plugin delivery path; do not invent a cache mutation command.

- [ ] **Step 6: Smoke-test the installed guard**

Run the installed `zentao-ai-repository preflight` against a synchronized allowed test branch and protected test branches. Confirm allowed branches have no `TARGET_BRANCH_MISMATCH`, while protected branches return `PROTECTED_BRANCH`.

- [ ] **Step 7: Report exact pushed revision and installation evidence**

Include branch, commit SHA, test count, installation command result, and smoke-test outputs.
