# Task V2-3 Report

## Outcome

- `bug_statistics()` now performs one official, read-only product catalog request.
- It never calls the synthetic statistics route and returns completeness-neutral
  values: `validatedProducts` is the number of structurally validated products in
  the checked page, while `complete` is always `0`.
- Raw catalog data is not retained in the result.

## TDD evidence

RED command:

`.venv\Scripts\python.exe -m pytest -q tests\integration\zentao\test_http_provider.py -k "user_history_and_statistics_contracts or bug_statistics_catalog_failure_is_sanitized"`

Result before implementation: 2 failed. Both failures proved that the old code
still requested `/api/bugs/statistics`; the malformed-catalog test also rejected
that route directly.

GREEN command: the same focused command after the minimal implementation.

Result: 2 passed, 62 deselected.

## Verification

- Provider and doctor-focused tests: 75 passed.
- Initial full pytest: 484 passed, 15 failed, 2 skipped; all 15 failures were due
  to the worktree virtual environment lacking the Windows `tzdata` package.
- Installed `tzdata` into the worktree virtual environment only; no dependency or
  source file was changed for that environment repair.
- Fresh full pytest: 499 passed, 2 skipped, 26 subtests passed.
- `ruff check .`: passed.
- `ruff format --check` on the two changed Python files: passed.
- Project mypy: no issues in 56 source files.
- `git diff --check`: passed.
- Editable provenance resolved to this worktree's `src/zentao_ai/__init__.py`.

## Real read-only doctor

Command: `zentao-ai doctor --project F:\每日工作 --json`

Exit code: 0. All nine checks passed: config, credentials, connection,
query-permission, repository, branch, tests, MCP executable, and report directory.
Only sanitized structural results were inspected. The catalog connection result
contained the two documented integer keys with no raw response. The scoped query
permission result contained no Bug items and reported unknown total coverage; no
values, credentials, headers, Bug data, or raw HTTP responses are recorded here.

## Concerns

- `complete: 0` deliberately prevents consumers from treating the one-page
  connection proof as exact product or Bug statistics.
- `tzdata` remains an environment requirement on this Windows runner but is not
  declared by the project; this pre-existing packaging concern is outside V2-3.
