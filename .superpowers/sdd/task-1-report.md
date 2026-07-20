# Task 1 Report

- status: DONE
- files changed:
  - `src/zentao_ai/zentao/http_provider.py`
  - `tests/integration/zentao/test_http_provider.py`
  - `.superpowers/sdd/task-1-report.md`
- RED test command: `uv run --extra dev pytest tests/integration/zentao/test_http_provider.py::test_query_user_bugs_adapts_official_bugs_envelope -vv`
  - Expected failure evidence: the official `bugs` envelope produced `result.items == ()`; assertion expected IDs `[2537, 3397]`.
  - The first literal `pytest` attempt could not start because pytest was not on PATH; `uv run --extra dev` established the valid test environment.
- Additional RED command: `uv run --extra dev pytest tests/integration/zentao/test_http_provider.py -k "query_user_bugs_adapts_official or query_user_bugs_rejects_unknown or query_user_bugs_rejects_official or query_user_bugs_retains_items" -vv`
  - Expected failure evidence: 4 selected tests failed because official bugs were discarded, unknown envelopes did not fail closed, missing official versions were not inspected, and contradictory pagination returned no candidates.
- GREEN test command: `uv run --extra dev pytest tests/integration/zentao/test_http_provider.py -vv`
  - Result: 80 passed in 0.61s.
- Static/scope checks: `git diff --check` and `uv run --extra dev ruff check src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py` both passed.
- implementation commit hash: `4f10192f155f6d4ab5adc9fcba44ff63f96480e4`
- self-review findings:
  - `query_user_bugs` calls only the configured user endpoint and sends only `page` and `pageSize`; it does not load the product catalog.
  - Existing `items` responses use `_snapshot`; official `bugs` responses use `_official_snapshot`.
  - Unknown/malformed envelopes and missing stable versions remain sanitized contract failures.
  - Complete, internally consistent pagination is preserved; missing, invalid, or contradictory metadata retains parsed candidates with `total=-1` and `pages=None`.
  - No Zentao write endpoint, write permission, or write behavior was changed or invoked.
- concerns: none.

## Review Fixes

- status: DONE
- RED command: `uv run --extra dev pytest tests/integration/zentao/test_http_provider.py -k "underfilled_nonempty_pages or falls_back_when_response_pagination_mismatches_request" -vv`
  - Result: 4 failed, 80 deselected. Both underfilled-page cases incorrectly trusted `total`/`pages`; mismatched response coordinates incorrectly replaced the requested page or page size.
- GREEN command: `uv run --extra dev pytest tests/integration/zentao/test_http_provider.py -vv`
  - Result: 84 passed in 0.61s.
- Static checks: targeted Ruff check and `git diff --check` passed.
- fixes:
  - Exact expected item counts are now required for both full and final pages before pagination metadata is trusted.
  - Response `page` and `pageSize` mismatches retain parsed items, return the requested coordinates, and report unknown coverage.
- concerns: none.

## Mypy Gate Fix

- status: DONE
- initial command: `uv run --extra dev mypy src`
  - Result: 3 errors in `http_provider.py` from arithmetic and `Coverage.total` using values typed as `Any | None`.
- change: normalize validated `total` and `pages` metadata into explicit `int | None` locals and explicitly narrow `Coverage.total`; runtime behavior is unchanged.
- verification command: `uv run --extra dev mypy src`
  - Exact result: `Success: no issues found in 57 source files`
- regression command: `uv run --extra dev pytest tests/integration/zentao/test_http_provider.py -vv`
  - Exact result: `84 passed in 0.49s`
- concerns: none.

## Production Contract Diagnostic Review Fix

- status: DONE_WITH_CONCERNS
- commits: `59d53699c077e9023f55f71da1e8c621ec530b23` (initial opt-in reproduction); `9e0de5aab979388eb05837174a911f3b437faecc` (independent operation classification).
- fixes:
  - The opt-in diagnostic now captures each public operation separately and executes `query_bug_history` even if `query_user_bugs` fails, using a harmless fallback identifier only for the fail-closed call.
  - Assertions are deferred until both operations are captured. Failure output contains only boolean checks and `OperationEvidence`, never Bug objects or response bodies.
  - The report distinguishes the probe-local JSON `ValueError` from the provider's pre-request `ContractError` and labels the Bug-detail observation as unverified.
- sanitized evidence:
  - `query_user_bugs`: exception_class=none, status_category=2xx, top_level_keys=(blockID, branch, branchTagOption, browseType, bugs, builds, currentModuleID, executions, from, idList, memberPairs, modulePairs, modules, orderBy, pager, param, plans, product, products, projectPairs, status, stories, tasks, title, users), bugs=dict, items=NoneType, actions=NoneType, pager=dict.
  - `query_bug_history`: exception_class=ContractError, status_category=not_requested, top_level_keys=(), bugs=NoneType, items=NoneType, actions=NoneType, pager=NoneType. The provider fails closed before making an HTTP request because no history endpoint is configured.
  - A prior temporary direct probe received HTTP 404 (4xx) on an assumed standalone history route. Its `ValueError` came only from attempting to decode that non-JSON body; it was not raised by `query_bug_history` and is not a production contract classification.
  - A separate read-only Bug-detail response had top_level_keys=(actions, bug, status) and actions=list. This is unverified as an official history contract and is neither asserted by the diagnostic nor wired into production code.
- commands and results:
  - `$env:ZENTAO_PRODUCTION_CONTRACT_TEST='1'; .superpowers\\venv\\Scripts\\python.exe -m pytest -q tests\\integration\\zentao\\test_production_contract_shapes.py` -> `1 failed`; sanitized evidence showed `query_user_bugs` passed and `query_bug_history` failed closed as `ContractError`/`not_requested`.
  - `.superpowers\\venv\\Scripts\\python.exe -m pytest -q tests\\integration\\zentao\\test_production_contract_shapes.py` -> `1 skipped`.
  - `.superpowers\\venv\\Scripts\\python.exe -m ruff check tests\\integration\\zentao\\test_production_contract_shapes.py` -> `All checks passed!`.
  - `.superpowers\\venv\\Scripts\\python.exe -m pytest -q` -> `560 passed, 3 skipped, 26 subtests passed`.
- concerns: History remains deliberately unavailable until a verified contract is implemented in a later task; no production code or configuration changed here.
