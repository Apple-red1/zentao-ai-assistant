# Local Title Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve assigned Bugs with missing provider routing and derive safe candidate repositories from account-local title/layer mappings.

**Architecture:** Extend validated application configuration with generic local routing entries, then enhance the existing pure router to choose a frontend/backend repository from one title marker plus unambiguous layer keywords. The read workflow enriches missing routing before analysis and retains ambiguous Bugs as `NEEDS_ENGINEER_REVIEW`; the real mapping remains only in the workspace YAML.

**Tech Stack:** Python 3.11+, Pydantic 2, pytest, PyYAML.

## Global Constraints

- Real account-specific mappings remain only in project-local `.codex/zentao-ai-bug.yaml`.
- Committed source, docs, defaults, and tests contain only generic schema or synthetic mappings.
- Provider routing wins when already valid.
- Ambiguous or missing routing never removes a Bug and never authorizes code writes.

---

### Task 1: Validated local routing configuration

**Files:**
- Modify: `src/zentao_ai/config/models.py`
- Test: `tests/unit/config/test_config.py`

**Interfaces:**
- Produces: `TitleRoutingConfig(marker: str, frontendRepository: str, backendRepository: str, frontendKeywords: list[str], backendKeywords: list[str])`
- Produces: `AppConfig.titleRouting: list[TitleRoutingConfig]`

- [ ] **Step 1: Write failing tests** for accepted synthetic mappings and rejection of duplicate normalized markers, equal layer repositories, and repository keys absent from `repositories`.
- [ ] **Step 2: Run** `pytest tests/unit/config/test_config.py -q`; expect failures because `titleRouting` is forbidden.
- [ ] **Step 3: Implement** `TitleRoutingConfig` with trimmed non-empty fields and an `AppConfig` model validator that normalizes markers with NFC/casefold and checks repository references.
- [ ] **Step 4: Run** `pytest tests/unit/config/test_config.py -q`; expect all tests to pass.
- [ ] **Step 5: Commit** tests and configuration model changes.

### Task 2: Pure title-and-layer routing

**Files:**
- Modify: `src/zentao_ai/routing/router.py`
- Test: `tests/unit/routing/test_router.py`

**Interfaces:**
- Consumes: `AppConfig.titleRouting`
- Produces: `route_bug(snapshot: routing.models.BugSnapshot, config: AppConfig) -> RoutingDecision`

- [ ] **Step 1: Write failing tests** using synthetic markers for a frontend link case, backend API case, ambiguous layer case, conflicting marker case, and unmatched marker case.
- [ ] **Step 2: Run** `pytest tests/unit/routing/test_router.py -q`; expect title-mapped cases to fail with no selected repository.
- [ ] **Step 3: Implement** exact-one-marker matching, expanded generic frontend terms (`button`, `layout`, `interaction`, `click` and Chinese equivalents), local keyword extensions, and unique-layer repository selection. Preserve existing exact-scope/provider-compatible behavior.
- [ ] **Step 4: Run** `pytest tests/unit/routing/test_router.py -q`; expect all tests to pass.
- [ ] **Step 5: Commit** router and unit tests.

### Task 3: Preserve and enrich assigned Bugs in read reports

**Files:**
- Modify: `src/zentao_ai/zentao/models.py`
- Modify: `src/zentao_ai/workflows/models.py`
- Modify: `src/zentao_ai/workflows/runtime.py`
- Test: `tests/unit/workflows/test_runtime_matrix.py`

**Interfaces:**
- Produces: routing metadata on `BugRunResult` (`selectedRepository`, `layer`, `matchedKeywords`, `routingStatus`).
- Consumes: provider `BugSnapshot.title`, `steps`, and optional structured `routing`.

- [ ] **Step 1: Write a failing workflow test** whose provider returns an assigned Bug with `routing=None`; assert the Bug remains in `bugResults`, receives title-derived routing when unambiguous, and an ambiguous Bug receives `NEEDS_ENGINEER_REVIEW` with `completeness=PARTIAL`.
- [ ] **Step 2: Run** the focused test and confirm it fails because routing is not evaluated or serialized.
- [ ] **Step 3: Implement** a conversion from provider snapshot to pure router input, prefer existing valid provider routing, serialize routing evidence on each result, and force human review/partial completeness only for unresolved routing.
- [ ] **Step 4: Run** `pytest tests/unit/workflows/test_runtime_matrix.py -q`; expect all tests to pass.
- [ ] **Step 5: Commit** workflow and model changes.

### Task 4: Local mapping and end-to-end verification

**Files:**
- Modify locally only: `F:/每日工作/.codex/zentao-ai-bug.yaml`
- Test: existing CLI and full test suite

**Interfaces:**
- Adds four local values under `titleRouting`: two business markers and their frontend/backend repository keys.

- [ ] **Step 1: Add the approved real mappings** to the local YAML with `apply_patch`; do not add them to the Git worktree.
- [ ] **Step 2: Validate config** with `run-ledger.py validate-config`; expect `valid:true` and redacted output containing the generic local routing structure.
- [ ] **Step 3: Run focused suites:** `pytest tests/unit/config/test_config.py tests/unit/routing/test_router.py tests/unit/workflows/test_runtime_matrix.py -q`.
- [ ] **Step 4: Run full verification:** `pytest -q`, `ruff check src tests`, and `mypy src`.
- [ ] **Step 5: Run a fresh read-only personal report/query** and verify the two live assigned Bugs are retained with the expected candidate repositories, without comments or code writes.
- [ ] **Step 6: Review** `git diff --check`, `git status --short`, and ensure the real mapping is absent from committed/worktree files.
