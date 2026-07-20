# Zentao Assignee Pagination Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure personal Bug queries find assignee matches beyond the first upstream page when the official collection omits pagination metadata.

**Architecture:** Keep `HttpZentaoProvider` as the HTTP contract boundary. Add an explicitly incomplete, bounded unknown-pagination scan that continues only when no trustworthy pagination contract has ever been established; retain all existing duplicate, overlap, contradiction, and maximum-page safety stops.

**Tech Stack:** Python 3.11+, HTTPX, pytest, Ruff, mypy, pipx, Zentao MCP.

## Global Constraints

- Do not write, comment on, assign, resolve, close, or otherwise mutate any Zentao Bug.
- Unknown pagination must remain `coverage.total=-1` and `coverage.pages=None`.
- Stop unknown-pagination scans on an empty page, repeated page, cross-page Bug ID overlap, or `_MAX_USER_BUG_PAGES`.
- Preserve unrelated dirty worktree files and avoid unrelated refactoring.

---

### Task 1: Reproduce and fix missing-metadata pagination

**Files:**
- Modify: `tests/integration/zentao/test_http_provider.py`
- Modify: `src/zentao_ai/zentao/http_provider.py:495-565`

**Interfaces:**
- Consumes: `HttpZentaoProvider.query_user_bugs(user, page=1, page_size=20) -> BugPage`
- Produces: bounded scanning behavior for official Bug collections without valid pagination metadata.

- [ ] **Step 1: Write the failing regression test**

Add a test that returns an unrelated Bug on page 1, the requested assignee on page 2, and an empty list on page 3, with no pagination fields:

```python
def test_query_user_bugs_scans_until_empty_when_official_metadata_is_missing() -> None:
    requested_pages: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_page = int(request.url.params["page"])
        requested_pages.append(requested_page)
        rows = {
            1: [{"id": 1, "status": "active", "assignedTo": "other", "lastEditedDate": "v1"}],
            2: [{"id": 2, "status": "active", "assignedTo": "xuli", "lastEditedDate": "v2"}],
        }.get(requested_page, [])
        return httpx.Response(200, json={"bugs": rows})

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli", page_size=1)

    assert requested_pages == [1, 2, 3]
    assert [item.id for item in result.items] == [2]
    assert result.coverage.total == -1
    assert result.coverage.pages is None
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest tests/integration/zentao/test_http_provider.py::test_query_user_bugs_scans_until_empty_when_official_metadata_is_missing -vv`

Expected: FAIL because the current implementation requests only page 1 and returns no matching Bug.

- [ ] **Step 3: Implement the minimal pagination fix**

Replace the unconditional `metadata is None` stop with this state-aware branch after duplicate and overlap checks:

```python
if repeated or overlaps_prior_page:
    break
if metadata is None:
    if expected_total is not None or expected_pages is not None or not bugs:
        break
    continue
```

Leave `complete=False` in this path so coverage remains explicitly incomplete.

- [ ] **Step 4: Run focused RED/GREEN verification**

Run the focused test again and expect PASS. Then run:

`python -m pytest tests/integration/zentao/test_http_provider.py -k "query_user_bugs" -vv`

Expected: all selected tests pass, including existing repeated-page, contradictory-pager, overlap, and maximum-page cases.

- [ ] **Step 5: Run static checks for changed files**

Run:

```powershell
python -m ruff check src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py
python -m ruff format --check src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py
python -m mypy src
```

Expected: all commands exit 0.

### Task 2: Verify, reinstall, and exercise the production query

**Files:**
- No source files beyond Task 1.
- Runtime install target: existing pipx environment `zentao-ai-assistant`.

**Interfaces:**
- Consumes: locally tested source tree.
- Produces: installed MCP runtime whose `query_my_bugs(status="unclosed", page=1, pageSize=100)` includes Bug 2537 and 3397.

- [ ] **Step 1: Run full repository verification**

Run:

```powershell
python -m pytest -q
python -m ruff check src tests
python -m mypy src
git diff --check
```

Expected: all commands exit 0 with zero test failures.

- [ ] **Step 2: Review the exact change**

Run `git diff -- src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py` and confirm only the regression test and minimal pagination branch changed.

- [ ] **Step 3: Reinstall the local package**

Run:

```powershell
pipx install --force "C:\Users\wwtlove66\.codex\.tmp\marketplaces\zentao-team\.worktrees\zentao-query-contract-fix"
```

Expected: `zentao-ai-assistant` is reinstalled successfully from the fixed source tree.

- [ ] **Step 4: Restart or refresh the MCP process if required**

Confirm the active `mcp__zentao__` server loads the reinstalled package rather than the pre-fix process image. If the current process cannot refresh in place, report that restart requirement explicitly and do not claim production verification.

- [ ] **Step 5: Verify the real read-only query**

Call `mcp__zentao__query_my_bugs` with `{status: "unclosed", page: 1, pageSize: 100}`.

Expected: structured results include Bug IDs 2537 and 3397 assigned to `weiwenting`; no write tools are called.

- [ ] **Step 6: Commit only the intended source and test changes**

Run:

```powershell
git add -- src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py
git commit -m "fix: scan assignee bugs without pagination metadata"
```

Do not stage `.superpowers/sdd/task-2-report.md`, `.superpowers/sdd/task-4-report.md`, `uv.lock`, or any unrelated file.
