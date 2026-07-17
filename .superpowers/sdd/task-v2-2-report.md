# Task V2-2 Report

## RED

- Added focused provider tests for Unicode-safe exact scope matching, unknown and ambiguous scopes, official request parameters and field normalization, stable-version fallback, missing stable version, malformed `bugs` envelopes, deterministic cross-product deduplication, and coverage totals.
- Command: `.venv\Scripts\python.exe -m pytest -q tests/integration/zentao/test_http_provider.py -k 'query_my_bugs_resolves or query_my_bugs_unknown or query_my_bugs_deduplicates or query_my_bugs_uses_nonblank or query_my_bugs_rejects_malformed or query_my_bugs_missing_stable'`
- Result before production edits: 8 failed for the expected reason: `query_my_bugs()` still called the synthetic `/api/bugs/mine` route.

## GREEN

- Replaced only `query_my_bugs()` with catalog-scoped official API v2 aggregation.
- Added private normalized scope resolution, official Bug normalization, stable-version validation, deterministic ID deduplication, and truthful unknown coverage (`total=-1`, `pages=None`).
- Kept `query_user_bugs()`, its shared legacy normalization, and all writes unchanged.
- Focused result after implementation: 8 passed.
- Full provider result: 50 passed.

## Lint and Types

- Ruff format: 2 changed files formatted.
- Ruff check: all checks passed.
- Strict mypy for `src/zentao_ai/zentao/http_provider.py`: success, no issues.
- `git diff --check`: clean.

## Self-review

- Confirmed configured scope order controls aggregation and first occurrence wins.
- Confirmed normalized product ambiguity is based on multiple unique IDs; duplicate catalog entries for the same ID do not create false ambiguity.
- Confirmed malformed envelopes and Bug values never enter error text.
- Confirmed unknown server totals and unresolved scopes cannot be interpreted as complete coverage.
- Confirmed production diff does not modify `query_user_bugs()` or write methods.

## Commit

- Commit created and report included by amend: `feat: query scoped Bugs through Zentao v2`.

## Pagination review fix (2026-07-17)

- RED: focused global-pagination tests failed because the implementation requested the public page independently from every product, summed overlapping product totals, and loaded only catalog page 1.
- Added coverage for a global page 2 spanning products, exact deduplicated overlap totals, overlap with missing metadata, early/incomplete traversal, and scope resolution from catalog page 2.
- GREEN: product Bug reads now start at page 1, merge/deduplicate in configured order, stop safely once the requested global window is available, and slice to at most `page_size`.
- Exact `total/pages` now come only from a fully traversed deduplicated union with consistent totals; early, repeated, bounded, unresolved, ambiguous, or metadata-incomplete traversal returns `total=-1`, `pages=None`.
- Catalog traversal is bounded to 100 pages of 100 products and rejects repeated pages as incomplete, preventing a partially observed catalog from being used to guess a scope.
- Focused command: `.venv\Scripts\python.exe -m pytest -q tests/integration/zentao/test_http_provider.py -k 'applies_page_to_global or reports_exact_deduplicated or overlap_with_missing or resolves_scope_from_later or resolves_unicode or deduplicates_in_configured'`.
- Focused result: `6 passed, 48 deselected`.
- Full provider command: `.venv\Scripts\python.exe -m pytest -q tests/integration/zentao/test_http_provider.py`.
- Full provider result: `54 passed in 0.43s`.
- Ruff check command: `.venv\Scripts\python.exe -m ruff check src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py`; result: `All checks passed!`.
- Ruff format check command: `.venv\Scripts\python.exe -m ruff format --check src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py`; result: `2 files already formatted`.
- Strict mypy command: `.venv\Scripts\python.exe -m mypy --strict src/zentao_ai/zentao/http_provider.py`; result: `Success: no issues found in 1 source file`.
- Diff check command: `git diff --check`; result: clean with exit code 0.
- Pagination fix commit: `1380fd7 fix: apply global pagination to scoped Bugs`.

## Exhaustion review fix (2026-07-17)

- RED: a capped non-empty Bug page without totals was treated as complete and allowed a later product into the global window; a capped catalog page was treated as complete and allowed a later same-normalized-name ambiguity to be missed.
- Added regression tests for capped Bug pages without totals, short Bug pages whose advertised total has remaining items, and capped catalog pages with a later ambiguous product name.
- Bug traversal now advances the current product until consistent `total` and `pages` prove completion, an empty page proves exhaustion, the global window permits an early unknown stop, or repeated/max-page safeguards fail closed.
- Catalog traversal now uses consistent advertised `total/pages` or an observed empty page; non-empty short pages alone never prove catalog completeness, and incomplete catalogs are never used for scope resolution.
- An observed empty page permits an exact deduplicated union even when prior metadata was missing, because traversal itself proves exhaustion.
- Focused RED command: `.venv\Scripts\python.exe -m pytest -q tests/integration/zentao/test_http_provider.py -k 'continues_capped_product or short_page_with_remaining or capped_catalog_page'`; result before implementation: `2 failed, 1 passed, 54 deselected`.
- Focused GREEN result after implementation: `3 passed, 54 deselected`.
- Final provider command: `.venv\Scripts\python.exe -m pytest -q tests/integration/zentao/test_http_provider.py`; result: `57 passed in 0.51s`.
- Final Ruff check: `All checks passed!`; format check: `2 files already formatted`.
- Final strict mypy: `Success: no issues found in 1 source file`; `git diff --check`: clean.

## Premature-empty review fix (2026-07-17)

- RED command: `.venv\Scripts\python.exe -m pytest -q tests/integration/zentao/test_http_provider.py -k 'premature_empty'`; result before implementation: `2 failed, 57 deselected`.
- Added Bug and catalog regressions proving an empty page cannot establish exhaustion when it arrives before a previously trusted `total/pages` contract is satisfied.
- Product traversal now returns incomplete immediately on a contradictory empty page, so later-product items cannot corrupt configured global order.
- Catalog traversal now marks a premature empty page incomplete and therefore performs no scope resolution.
- Empty-page exhaustion without prior trusted metadata remains supported.
- Focused GREEN: `2 passed, 57 deselected`; full provider: `59 passed in 0.50s`.

## Sticky metadata-conflict review fix (2026-07-17)

- RED command: `.venv\Scripts\python.exe -m pytest -q tests/integration/zentao/test_http_provider.py -k 'conflicting_product_metadata or conflicting_catalog_metadata'`; corrected conflict fixtures produced `2 failed, 59 deselected`.
- Added Bug and catalog regressions with conflicting non-empty-page `total/pages` followed by an empty page.
- Metadata inconsistency is now sticky: a later empty page cannot restore exact coverage or catalog completeness after any trusted metadata conflict.
- Metadata absent throughout remains distinct and can still use an observed empty page as exhaustion proof.
- Focused GREEN: `2 passed, 59 deselected`; full provider before final lint gate: `61 passed in 0.40s`.

## Invalid-present metadata review fix (2026-07-17)

- RED command: `.venv\Scripts\python.exe -m pytest -q tests/integration/zentao/test_http_provider.py -k 'invalid_present_product or invalid_present_catalog'`; result: `2 failed, 61 deselected`.
- Added Bug and catalog regressions where non-empty pages contain present but invalid `total/pages` values and are followed by an empty page.
- Traversal now records a sticky `invalid_metadata_seen` state separately from metadata absence; an empty page cannot restore exactness/completeness after invalid-present metadata.
- Truly absent metadata remains eligible for empty-page exhaustion proof.
- Focused GREEN: `2 passed, 61 deselected`; full provider before final lint gate: `63 passed in 0.38s`.
