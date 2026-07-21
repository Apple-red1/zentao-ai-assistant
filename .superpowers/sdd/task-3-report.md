# Task 3 Report: structured Bug history from detail actions

## Implemented

- Production runtime now configures `bugHistory=/api.php/v2/bugs/{bug_id}`.
- `query_bug_history()` performs an independent GET of the configured detail route, without pagination query parameters.
- The official detail adapter strictly requires `actions` to be a list or a mapping whose values are mappings; missing, scalar, and non-mapping entries fail closed.
- Every action is normalized through `BugHistoryEntry`, retaining `id`, `action`, `actor`, `idempotencyKey`, and `contentHash` while preserving recursively sanitized immutable raw fields.
- Official actions are validated as a complete collection before local slicing. Coverage is exact: requested page/page size, total action count, and ceiling-divided page count.
- Pagination rejects booleans, non-integers, non-positive values, and page sizes over 1000 before any request.
- Existing custom `items` history endpoints retain their server-pagination behavior.
- The opt-in production contract test now gathers arbitrary-user and history evidence independently. History uses `ZENTAO_PRODUCTION_HISTORY_BUG_ID` when supplied, otherwise a read-only Bug discovered through `query_my_bugs`; an empty incomplete arbitrary-user result no longer blocks history verification.

## TDD and root-cause evidence

- RED 1: the first official-actions regression failed because the old adapter sent `page=2&pageSize=2` to the detail endpoint; without that assertion it would also have interpreted the absent `items` key as empty history.
- GREEN 1: after strict actions adaptation and local pagination, the focused regression passed.
- RED 2: the runtime construction assertion failed because production configured `bugHistory=None`.
- GREEN 2: production runtime now configures the verified detail route.
- Production acceptance initially exposed an independent test-design defect: the fixed arbitrary assignee returned an empty incomplete page, so history was not called. The test now selects its history Bug independently and no longer requires that user page to be nonempty.

## Verification

- Focused history tests: `16 passed, 91 deselected`.
- Relevant runtime and CLI tests: `17 passed`.
- Provider integration suite: `107 passed` (run before the final production-test-only adjustment).
- Full suite: `577 passed, 3 skipped, 26 subtests passed`.
- Ruff on all changed Python files: passed.
- mypy: success, no issues in 57 source files.
- `git diff --check`: passed.
- Opt-in production contract test with an in-memory, non-printed Bug ID: `1 passed`.

## Production safety and shape evidence

- Verification performed GET requests only; no Bug or comment was created, changed, assigned, resolved, closed, activated, or deleted.
- The production detail action collection normalized successfully: 2 entries, exact total 2, one page. The first normalized field types were `id=int`, `action=str`, `actor=str`, and immutable sanitized `raw=mappingproxy`.
- No credentials, identifiers, authorization headers, cookies, or raw production responses were printed or persisted.

## Concerns

- In the current production configuration, both the fixed arbitrary-user query and `query_my_bugs` returned empty incomplete pages. Automated history acceptance therefore needs `ZENTAO_PRODUCTION_HISTORY_BUG_ID` unless discovery later yields a Bug. The committed test fails with a safe instruction when neither source is available rather than silently skipping history.

## P1 review fix: semantic action validity

- Root cause: `_actions()` checked only that each entry was a mapping, while `BugHistoryEntry` supplies defaults and ignores unknown fields. Empty, unknown-only, and credential-only mappings therefore became blank history entries.
- RED: the three focused reviewer shapes (`{}`, `{"unknown": 1}`, and a credential-only mapping) all initially failed to raise `ContractError`. The final boundary suite also covers blank IDs/actions and a boolean ID.
- Fix: official detail actions now require a nonboolean, nonblank string/integer `id` and a nonblank string `action` before normalization. `actor` remains optional per the existing `BugHistoryEntry` contract.
- Compatibility: this validation applies only to official `actions`; custom `items`, sanitized raw fields, idempotency fields, and local pagination are unchanged.
- GREEN focused verification: `27 passed, 89 deselected`, covering official history and custom reconciliation behavior.
- Fresh full verification: `586 passed, 3 skipped, 26 subtests passed`.
- Fresh static verification: Ruff passed; mypy reported no issues in 57 source files; `git diff --check` passed.
