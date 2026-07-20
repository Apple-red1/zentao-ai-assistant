# Plugin Wrapper CLI Dispatch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make plugin wrapper scripts independent of the Python interpreter that launches them by forwarding to console scripts installed with the supported CLI distribution.

**Architecture:** Package three internal companion executables backed by existing `main` callables. Replace direct imports in the four plugin wrappers with standard-library PATH discovery and shell-free subprocess forwarding; the doctor wrapper prefixes the public `doctor` subcommand.

**Tech Stack:** Python 3.11+, Python packaging console scripts, pytest.

## Global Constraints

- Wrappers must work under isolated Python `-I -S` when the required launcher is on PATH.
- Do not inspect pipx directories, virtual environments, credentials, or platform-specific launcher internals.
- Do not import `zentao_ai`, mutate `sys.path`, install dependencies, or use `shell=True` in wrappers.
- Preserve stdin, stdout, stderr, argument order, and child exit codes.
- Missing launchers must emit the existing supported GitHub/pipx installation instruction.

---

### Task 1: Package companion console scripts

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/contract/test_plugin_package.py`

**Interfaces:**
- Produces: `zentao-ai-state -> zentao_ai.state.cli:main`
- Produces: `zentao-ai-repository -> zentao_ai.repository.cli:main`
- Produces: `zentao-ai-render-report -> zentao_ai.reporting.cli:main`

- [ ] **Step 1: Write a failing metadata test** that parses `pyproject.toml` and asserts the three exact companion script mappings.
- [ ] **Step 2: Run** `pytest tests/contract/test_plugin_package.py -q`; expect the new assertion to fail because the companion keys are absent.
- [ ] **Step 3: Add the three mappings** under `[project.scripts]` without changing the public `zentao-ai` mapping.

```toml
zentao-ai-state = "zentao_ai.state.cli:main"
zentao-ai-repository = "zentao_ai.repository.cli:main"
zentao-ai-render-report = "zentao_ai.reporting.cli:main"
```
- [ ] **Step 4: Run** `pytest tests/contract/test_plugin_package.py -q`; expect the metadata test to pass.
- [ ] **Step 5: Commit** `pyproject.toml` and the metadata test.

### Task 2: Standard-library wrapper forwarding

**Files:**
- Modify: `plugins/zentao-ai-bug/scripts/run-ledger.py`
- Modify: `plugins/zentao-ai-bug/scripts/direct-branch-guard.py`
- Modify: `plugins/zentao-ai-bug/scripts/render-report.py`
- Modify: `plugins/zentao-ai-bug/scripts/doctor.py`
- Test: `tests/contract/test_plugin_package.py`

**Interfaces:**
- Each wrapper defines a constant tuple `COMMAND` and forwards `[*COMMAND, *sys.argv[1:]]` to the located executable.
- Command tuples are respectively `("zentao-ai-state",)`, `("zentao-ai-repository",)`, `("zentao-ai-render-report",)`, and `("zentao-ai", "doctor")`.

- [ ] **Step 1: Replace the old import-only contract test** with failing isolated-Python tests that monkeypatch only standard-library `shutil.which` and `subprocess.call`, execute each wrapper via `runpy.run_path`, and assert exact forwarded argv and exit code.
- [ ] **Step 2: Run** the focused wrapper tests; expect failure because current wrappers import `zentao_ai` under `-I -S`.
- [ ] **Step 3: Implement each wrapper** using `shutil.which`, `subprocess.call` with `shell=False` by default, the existing installation message, and `SystemExit` with the child result.

```python
#!/usr/bin/env python3
import shutil
import subprocess
import sys

COMMAND = ("zentao-ai-state",)
executable = shutil.which(COMMAND[0])
if executable is None:
    raise SystemExit('Install the CLI with: pipx install "git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source". See docs/plugin-installation.md.')
raise SystemExit(subprocess.call([executable, *COMMAND[1:], *sys.argv[1:]]))
```
- [ ] **Step 4: Run** the focused wrapper tests; expect forwarding and missing-command tests to pass.
- [ ] **Step 5: Commit** the four wrappers and contract tests.

### Task 3: Package and live plugin verification

**Files:**
- No source changes expected.

**Interfaces:**
- Consumes the built distribution and installed companion launchers.

- [ ] **Step 1: Run focused tests:** `pytest tests/contract/test_plugin_package.py tests/unit/state tests/unit/repository tests/test_render_report.py -q`.
- [ ] **Step 2: Run full verification:** `pytest -q`, `ruff check src tests`, and `mypy src`.
- [ ] **Step 3: Install the current local checkout with pipx** and verify `Get-Command zentao-ai-state`, `zentao-ai-repository`, and `zentao-ai-render-report` resolve.
- [ ] **Step 4: Refresh the local plugin cache through the supported local plugin installation flow, preserving local project configuration.**
- [ ] **Step 5: Re-run the original bundled-Python command:** `run-ledger.py validate-config --config F:\每日工作\.codex\zentao-ai-bug.yaml`; expect exit 0 and `valid:true`.
- [ ] **Step 6: Run the live read-only personal report and confirm two assigned Bugs remain visible; do not write comments, Bug fields, or code.**
- [ ] **Step 7: Check** `git diff --check` and `git status --short`; leave unrelated `.codex-marketplace-install.json` untracked and unstaged.
