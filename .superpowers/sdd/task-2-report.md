# Task 2 Report: Retain Versionless Rows in the HTTP Provider

## Outcome

Implemented degraded official Bug normalization while preserving strict detail
reads by default.

- Official user-list rows with valid IDs are retained without a stable version.
- Versionless snapshots expose `version=None`, `snapshotVersion=None`, and
  `snapshotStable=False`.
- Missing title/status/priority degrade to `"unknown"`; missing assignee remains
  `None`.
- Numeric priorities normalize to the `P<n>` presentation form.
- User-list coverage counts unstable snapshots returned on the requested page.
- Invalid IDs remain item failures.
- Official list normalization no longer performs per-row detail requests.
- `query_bug_detail(..., allow_unstable=False)` remains strict by default;
  callers must explicitly request a versionless detail snapshot.
- Both provider protocols and existing test doubles accept the defaulted,
  keyword-only `allow_unstable` argument.

## TDD Evidence

RED command:

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/zentao/test_http_provider.py -k "without_stable_version or missing_presentation" -q
```

Observed: `2 failed, 1 passed, 148 deselected`. The failures were expected:
the provider still requested detail for a versionless row, and it filtered a
row whose assignee was absent.

GREEN command (same focused selection):

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/zentao/test_http_provider.py -k "without_stable_version or missing_presentation" -q
```

Observed: `3 passed, 147 deselected`.

## Verification

Task-focused provider and production-shape suite:

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/zentao/test_http_provider.py tests/integration/zentao/test_production_contract_shapes.py -q
```

Observed: `149 passed, 1 skipped`.

Full suite (run once as requested):

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Observed: `640 passed, 3 skipped, 35 subtests passed`.

Fresh changed-surface verification after updating protocol test doubles:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/integration/zentao/test_http_provider.py tests/integration/zentao/test_production_contract_shapes.py tests/contract/test_mcp_tools.py tests/e2e/test_workflow_parity.py tests/unit/workflows/test_closure_matrix.py tests/unit/workflows/test_operations.py tests/unit/workflows/test_repair_matrix.py tests/unit/workflows/test_runtime_matrix.py
```

Observed: `271 passed, 1 skipped`.

Ruff on all changed Python files: `All checks passed!`.

`mypy src` reports 9 existing baseline errors: eight Coverage constructor
calls do not provide Task 1's aliased `unstableSnapshots` default according to
the Pydantic mypy model, and one existing runtime argument is `str | None` where
`str` is required. The Coverage constructor changed in this task explicitly
supplies `unstableSnapshots`, so it is not among those failures.

## Self-review

- Default detail behavior remains fail-closed for missing stable versions.
- Only official list normalization opts into unstable snapshots in this task.
- Stable version fallback still accepts `version` when `lastEditedDate` is
  absent, invalid, or blank.
- Boolean versions and IDs remain invalid.
- Missing assignee retention is intentional per the brief; a present but
  nonmatching assignee is still filtered.
- The production contract assertion checks that coverage's unstable count
  matches returned versionless rows. Its live execution remains opt-in via
  `ZENTAO_PRODUCTION_CONTRACT_TEST=1` and was skipped locally.
