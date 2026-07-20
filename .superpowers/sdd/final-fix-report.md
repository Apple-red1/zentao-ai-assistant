# Final Review Fix Report

## Implemented

- Production/default Bug detail now calls `GET /api.php/v2/bugs/{bug_id}`, requires the official `{ "bug": ... }` envelope, and normalizes official fields with the same stable-version preference used by scoped queries.
- Custom detail endpoints retain the existing flat-envelope contract.
- Production/default Bug history is disabled and raises the stable sanitized `ContractError("query_bug_history: unsupported by official contract")` before any request. Injected custom history endpoints remain supported.
- `query_my_bugs()` validates integer pagination before catalog/network access: `page >= 1` and `1 <= page_size <= 1000`; booleans are rejected and errors expose no input values.
- Added the approved password-token design from main commit `8bb0ad2` without cherry-picking unrelated changes.

## TDD Evidence

- RED: focused regression selection produced 9 expected failures and 3 passes before production changes (official detail, default history, and seven invalid pagination cases failed).
- GREEN: the same focused selection passed 12/12 after the minimal fixes.

## Verification

- Provider integration: 76 passed.
- Provider/runtime/doctor-focused: 89 passed.
- Full pytest: 511 passed, 2 skipped, 26 subtests passed.
- Ruff check: passed.
- Changed-file Ruff format check: passed.
- Project mypy strict check: passed for 56 source files.
- `git diff --check`: passed.
- Real read-only doctor: all 9 required checks PASS (`config`, `credentials`, `connection`, `query-permission`, `repository`, `branch`, `tests`, `mcp-executable`, `report-directory`). No Zentao writes were performed.

## Self-review

- Default history fails before authentication or transport, so it cannot accidentally probe an unapproved route.
- Pagination validation precedes product-catalog resolution and contains no raw/user values.
- Existing credential precedence, password-token cache/retry behavior, global pagination assembly, user/write routes, configuration, and write guards are unchanged.
- The worktree virtual environment has no `pip` module, so an attempted editable reinstall could not run; import-path verification confirmed the doctor process uses this worktree's `src/zentao_ai` directly.
- No unresolved correctness or security concerns found.

## Final review follow-up (2026-07-17)

### Implemented

- Production assignee discovery now uses the read-only official `GET /api.php/v2/bugs` route with `browseType=assigntome`, adapts the safely observed ID-keyed `bugs` object, and maps `pager.pageID`, `recPerPage`, `recTotal`, and `pageTotal` into truthful coverage.
- ID-keyed assignee results are normalized into deterministic key order.
- Nonempty `scope_names` are transmitted as `scopeNames`; empty personal scopes are omitted, preserving team/scoped semantics without reintroducing a personal product-catalog dependency.
- Personal workflow documentation now describes configured-assignee-first discovery, default `status=unclosed`, optional exact leading full-width title tags, truthful pagination, and no product-catalog dependency. Team semantics and all write restrictions remain unchanged.

### TDD evidence

- RED 1: the focused tests failed because the request lacked `browseType=assigntome`, used `pageSize` instead of `limit`, did not transmit nonempty `scopeNames`, and rejected the observed ID-keyed `bugs` object / nested `pager` shape.
- GREEN 1: the focused `query_user_bugs` selection passed after the minimal route, request, envelope, and pager adaptation.
- RED 2: the observed-map ordering regression returned `[3397, 2537]` instead of required deterministic `[2537, 3397]`.
- GREEN 2: deterministic map-key normalization produced `[2537, 3397]` while retaining truthful coverage validation.

### Sanitized live read-only diagnostics and results

- The obsolete synthetic route failed at the HTTP boundary with sanitized status 404.
- The actual assignee list is an object with top-level `bugs` (ID-keyed object) and `pager` (object). Bug field-name inspection confirmed the official fields needed by the existing normalizer, including `id`, `title`, `status`, `openedBy`, `assignedTo`, and `lastEditedDate`. Pagination fields are `pageID`, `recPerPage`, `recTotal`, and `pageTotal`. No credentials, tokens, cookies, raw descriptions, or payload values are retained here.
- `AI建站`, `status=unclosed`: IDs `[2537]`; page 1, page size 20, total 1, pages 1; complete.
- `站点后台`, `status=unclosed`: IDs `[3397]`; page 1, page size 20, total 1, pages 1; complete.
- No title tag, `status=unclosed`: IDs `[2537, 3397]`; page 1, page size 20, total 2, pages 1; complete.
- Diagnostics and verification used GET/read-only operations only. No Zentao write endpoint or write tool was called.

### Verification and self-review

- Focused RED/GREEN evidence is recorded above. Final fresh commands are recorded in the handoff after completion.
- Reviewed the diff for scope preservation, fail-closed malformed-envelope handling, truthful pagination, documentation consistency, and accidental write calls. No write behavior was added or invoked.
- Commit hash is recorded in the handoff because a commit cannot contain its own object hash.

### Concerns

- The official assignee-list selector is authenticated-user based (`assigntome`); the provider retains its public `user` parameter and scoped API contract, but the live server route itself determines the authenticated assignee.

## Final identity-semantics follow-up (2026-07-17)

- RED: two parameterized regressions showed a different requested user and an absent authenticated identity were both silently routed to authenticated-user `assigntome`.
- GREEN: the official assignee route is now selected only when the requested user exactly matches the provider's authenticated username. Different-user or unknown-identity calls retain `GET /api/bugs/user/{user}` with `page`, `pageSize`, and any nonempty `scopeNames`.
- A matching-account regression proves `GET /api.php/v2/bugs` with `browseType=assigntome`, `page`, and `limit`.
- Personal workflow documentation again names `mcp__zentao__query_my_bugs` as the primary personal tool, with configured-account resolution internal to that capability. `query_user_bugs` is documented only for team/explicit-user reads.
- Live evidence, verification totals, and the follow-up commit are recorded in the handoff. All live calls were read-only; no Zentao write endpoint or tool was called.

## Final custom-endpoint follow-up (2026-07-17)

- RED: a custom `userBugs=/custom/users/{user}/assigned` regression observed the incorrect hardcoded `/api/bugs/user/{user}` path.
- GREEN: endpoint selection now has three explicit cases: matching authenticated account on configured official route uses official `assigntome`; different/unknown identity on configured official route uses the legacy explicit-user fallback; any custom configured endpoint is formatted and used exactly as configured.
- Custom and legacy explicit-user routes retain `page`, `pageSize`, and nonempty `scopeNames`; official matching-account calls retain `browseType`, `page`, and `limit`.
- Final verification totals, sanitized live IDs/pagination, and commit hash are recorded in the handoff. No Zentao write endpoint or tool was called.
