# Task 6 report: complete arbitrary-assignee coverage and detail enrichment

## Status

Implemented and locally verified. The official arbitrary-assignee query now performs bounded collection discovery before local filtering/pagination, enriches matching unstable rows through the read-only Bug detail route, and fails closed when a detail snapshot cannot prove a stable version and unchanged assignee.

Safety: only read-only Zentao operations were used. No Bug or comment was created, assigned, resolved, closed, activated, deleted, edited, or otherwise modified. Credentials, authorization data, raw production payloads, Bug IDs, titles, and descriptions were not printed or persisted.

## Behavior implemented

- Official `/api.php/v2/bugs` queries start at upstream page 1 and scan forward in a 100-page bounded loop.
- Completion is proven only from consistent response page, page-size, total, page-count, and row-count metadata. Missing/invalid metadata, repeated pages, contradictory totals/pages, premature exhaustion, or the page bound preserve safe matches but produce `Coverage(total=-1, pages=None)`.
- Raw rows are filtered by normalized `assignedTo.account` before snapshot validation, so malformed unrelated rows do not block the requested user.
- Matching rows are deduplicated by normalized Bug ID in deterministic upstream order.
- A matching row without `lastEditedDate` or `version` is enriched with read-only `query_bug_detail(id)`.
- Enriched detail is accepted only when it has a stable version, preserves the normalized Bug ID, and still belongs to the requested account.
- Missing IDs, missing detail versions, changed detail IDs, changed assignees, and invalid detail contracts raise operation-specific `query_user_bugs` `ContractError`s.
- Proven complete scans are filtered and paginated locally with an exact filtered `Coverage(total, pages)`. Incomplete scans use the requested local page with unknown coverage.
- Custom user endpoints and self-query behavior were left unchanged.

## TDD evidence

The focused pre-implementation RED run produced 8 expected failures:

- target Bug available only on upstream page 2;
- matching unstable row not enriched through detail;
- missing row ID;
- detail assignee mismatch;
- detail missing stable version;
- repeated upstream page;
- contradictory pager metadata;
- maximum-page exhaustion.

After the minimal implementation, the same focused selection passed: `8 passed, 116 deselected`. The preserved and updated arbitrary-user selection then passed: `24 passed, 100 deselected`.

## Verification

| Gate | Result |
| --- | --- |
| Focused arbitrary-user tests | 24 passed, 100 deselected |
| Provider integration suite | 124 passed |
| Mypy (`src`) | Success, no issues in 57 source files |
| Full non-production suite | 594 passed, 3 skipped, 26 subtests passed |
| Ruff on changed source/test | Passed |
| `git diff --check` | Passed |

Commit message: `fix: complete arbitrary assignee Bug discovery`.

## Sanitized production acceptance

Exactly four public account queries were attempted from the worktree source. The initial launcher path-encoding failure occurred before runtime construction and made zero account queries; the corrected run made the four required read-only queries and no additional production probes.

| Requested account | Outcome | Assignee verification | Coverage |
| --- | --- | --- | --- |
| `xuli` | Failed closed: `query_user_bugs: detail missing stable version` | No page returned | Unknown |
| `wangxiankun` | Empty page; scan completion proof unavailable | No returned mismatch | `total=-1`, `pages=None` |
| `duweijie` | Empty page; scan completion proof unavailable | No returned mismatch | `total=-1`, `pages=None` |
| `wuyuxuan` | Empty page; scan completion proof unavailable | No returned mismatch | `total=-1`, `pages=None` |

The three empty pages are not reported as zero Bugs because the upstream pager/total/count evidence did not prove collection completion. The exact sanitized classification is `completion_proof_unavailable`; no raw metadata was retained. The `xuli` result correctly remained a contract failure because at least one matching detail snapshot still lacked a stable version.

## Concerns

- Production data still contains at least one matching `xuli` Bug whose read-only detail snapshot lacks both accepted stable-version fields. The provider deliberately rejects the whole query rather than returning a partial snapshot set.
- The three other production queries returned empty incomplete pages. They cannot be treated as true zero results until the service provides internally consistent completion evidence within the configured bound.
- Pre-existing worktree changes in `.superpowers/sdd/task-2-report.md`, `.superpowers/sdd/task-4-report.md`, and the untracked `uv.lock` were not modified or included in this task's commit.

## Installed acceptance follow-up

Final installed-acceptance status: **BLOCKED** because execution was explicitly stopped after CLI help; the remaining required installed gates were not run.

- The exact active installed Zentao MCP process was identified by executable path and command line, then stopped to release its pipx virtual-environment lock. No unrelated Python process was touched.
- The first `pipx install --force <worktree>` attempt installed/replaced the application but exited nonzero in pipx's known stale-launcher Unicode scan.
- The single permitted retry used the proven workaround: only `uv.exe`, `uvw.exe`, and `uvx.exe` were temporarily moved from the exact exposure directory. The retry exited 0 and reported `zentao-ai-assistant 0.1.0` installed from this worktree with all four application launchers available.
- All three temporarily moved uv launchers were restored unconditionally and their restored paths were verified.
- Installed `zentao-ai --help` exited 0 and exposed the expected top-level `config`, `bugs`, `report`, and `mcp` commands.
- Per the stop instruction received immediately after CLI help, the four installed account queries, opt-in history for Bug 2537, config validation, and installed personal report were not executed. Earlier worktree-source acceptance is not substituted for these installed-state gates.
- No Zentao write operation or comment was invoked. No credentials or raw production payloads were printed.
- The stopped installed MCP server was not restarted during this follow-up.

## Final review fixes

Three Important review findings were corrected in one TDD wave:

1. A present non-mapping `pager` is now treated as invalid completion evidence; plausible top-level pagination fields are not used as a fallback.
2. Any normalized Bug ID repeated on a later upstream page marks the scan incomplete, even when the full page tuples differ. Deterministic first-seen deduplication and local pagination are preserved.
3. Official history detail responses now require a `bug` mapping whose normalized ID equals the requested Bug ID before any actions are accepted.

### RED

Command:

`.superpowers\venv\Scripts\python.exe -m pytest -q tests\integration\zentao\test_http_provider.py -k "malformed_present_pager or cross_page_id_overlap or wrong_bug_identity"`

Result before production changes: `5 failed, 124 deselected`. The failures were the expected three missing/invalid/wrong history Bug identity cases, exact coverage incorrectly accepted from a malformed present pager, and exact coverage incorrectly accepted across `[1, 2]` / `[2, 3]` page overlap.

### GREEN and final verification

| Command/gate | Result |
| --- | --- |
| Same targeted regression command | `5 passed, 124 deselected` |
| `.superpowers\venv\Scripts\python.exe -m pytest -q tests\integration\zentao\test_http_provider.py -k "query_user_bugs or official_collection or official_bug_history"` | `46 passed, 83 deselected` |
| `.superpowers\venv\Scripts\python.exe -m ruff check src\zentao_ai\zentao\http_provider.py tests\integration\zentao\test_http_provider.py` | All checks passed |
| `.superpowers\venv\Scripts\python.exe -m mypy src` | Success: no issues found in 57 source files |
| `.superpowers\venv\Scripts\python.exe -m pytest -q` | `599 passed, 3 skipped, 26 subtests passed in 58.74s` |
| `git diff --check` | Passed |

No live production probe or Zentao write was performed for these final review fixes.
