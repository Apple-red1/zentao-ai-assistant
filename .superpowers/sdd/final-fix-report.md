# Final Fix Report

## Final Fix

### Scope completed

- High-confidence exclusive routing now emits only the selected repository in
  `candidates`; ambiguous and missing-layer routes retain both diagnostic
  candidates. A real HTTP-provider snapshot now crosses `route_bug` into
  provider `RoutingData` and reaches the unchanged repair preflight gate.
- MCP errors now expose the approved stable codes
  `AUTHENTICATION_FAILED`, `IDENTITY_AMBIGUOUS`,
  `INVALID_RESPONSE_ENVELOPE`, `INVALID_BUG_CONTRACT`, and
  `MISSING_STABLE_VERSION`. Ambiguity details contain only sanitized account
  and display-name candidates; exception text and upstream secrets remain
  excluded.
- Official assignee queries now keep known matching `total` and `pages` when
  the upstream scan cardinality is trustworthy, while row failures still set
  `complete=false` and remain structured in `itemFailures`.
- Every supplied `memberPairs` record is validated fail-closed. Only exact
  duplicate identity records are deduplicated; normalized account and display
  collisions raise `AmbiguousIdentityError` with sanitized candidates.
- Plugin wording now separates configured personal/team report discovery from
  explicit read-only `session-visible` queries, which use neither report scope
  nor report membership.

No write or repository safety gate was weakened. No live Zentao write,
repository write, Git hosting operation, deployment, or external preflight was
performed.

### TDD evidence

- RED command:
  `.venv\Scripts\python.exe -m pytest -q tests/unit/routing/test_router.py tests/unit/workflows/test_repair_matrix.py::test_real_high_confidence_route_reaches_repository_preflight tests/integration/zentao/test_http_provider.py::test_query_user_bugs_rejects_ambiguous_member_pair_display_name tests/integration/zentao/test_http_provider.py::test_query_user_bugs_rejects_any_malformed_member_pair_record tests/integration/zentao/test_http_provider.py::test_query_user_bugs_rejects_normalized_account_collisions_as_ambiguous tests/integration/zentao/test_http_provider.py::test_query_user_bugs_retains_valid_official_rows_when_matching_rows_are_malformed tests/contract/test_mcp_tools.py::test_tool_errors_are_structured_sanitized_and_stable tests/contract/test_mcp_tools.py::test_bug_contract_errors_keep_their_approved_public_codes tests/contract/test_legacy_feature_inventory.py::LegacyFeatureInventoryTests::test_ad_hoc_query_and_routing_contracts_remain_explicit`
  -> `13 failed, 8 passed, 8 subtests passed`. Failures matched the reviewed
  defects: two-candidate trusted routes, repair rejection, missing ambiguity
  candidates, skipped malformed member record, normalized-account not-found,
  erased coverage totals/pages, incorrect public codes, and contradictory
  plugin wording.
- Initial GREEN with the same focused command ->
  `20 passed, 9 subtests passed`.
- Expanded affected-suite GREEN:
  `.venv\Scripts\python.exe -m pytest -q tests/unit/routing/test_router.py tests/unit/workflows/test_repair_matrix.py tests/integration/zentao/test_http_provider.py tests/contract/test_mcp_tools.py tests/contract/test_legacy_feature_inventory.py`
  -> `244 passed, 33 subtests passed`.
- First full-suite compatibility check ->
  `1 failed, 632 passed, 3 skipped, 35 subtests passed`; the sole failure was a
  stale runtime test that still expected both repositories for a
  high-confidence route. Updating that assertion to the approved
  `[selected]` contract produced `1 passed` for the focused compatibility test.
- Final focused GREEN after refactor and compatibility update ->
  `21 passed, 9 subtests passed`.

### Final verification

- `.venv\Scripts\python.exe -m pytest -q` ->
  `633 passed, 3 skipped, 35 subtests passed in 58.19s`.
- `.venv\Scripts\python.exe -m ruff check src tests` -> `All checks passed!`.
- `.venv\Scripts\python.exe -m mypy src` ->
  `Success: no issues found in 57 source files`.
- `git diff --check` -> clean.

### Self-review

- Re-read all four Important findings and the Minor wording finding against the
  final diff; each has a direct regression assertion and implementation path.
- Confirmed ambiguous/missing routing still fails closed and retains diagnostic
  candidates, while only exclusive high-confidence routes become unique.
- Confirmed request, authentication, permission, top-level envelope, detail
  request/envelope, and untrustworthy pagination failures remain outside the
  row-isolation boundary.
- Confirmed the repair workflow's permission, unique-routing, repository,
  branch, lease, confinement, snapshot, history, whitelist-test, diff, and
  comment authorization gates were not relaxed.
- Confirmed no delete, state-transition, assignee, commit, push, merge, deploy,
  checkout, or reset capability was added or invoked.
