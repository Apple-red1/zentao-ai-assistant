# Zentao Query Contract and Comments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair production-safe arbitrary-assignee Bug queries and structured Bug history reads, reinstall the local CLI/MCP package, and enable gated comments in the project configuration.

**Architecture:** Keep `HttpZentaoProvider` as the only HTTP-contract adapter. Use the official product Bug collection as the read-only fallback for arbitrary assignees, filtering normalized `assignedTo.account` locally with explicit incomplete coverage; obtain history from an explicitly configured structured endpoint and normalize both `items` and `actions` envelopes without accepting unknown payloads. Runtime wiring selects only documented/read-only endpoints, while the existing workflow continues to enforce snapshot, cooldown, history, idempotency, and confirmation gates for comments.

**Tech Stack:** Python 3.11+, httpx, Pydantic 2, pytest, Typer, pipx, YAML.

## Global Constraints

- Unknown response envelopes, missing stable Bug versions, authentication failures, and permission failures must fail closed.
- Never create, assign, resolve, close, activate, delete, or otherwise change a Bug's state or assignee.
- `commentEnabled: true` only enables comments after creator, snapshot, structured history, cooldown, deterministic idempotency, fixed-body, and `confirm:true` checks pass.
- Tests and diagnostics must not print tokens, passwords, cookies, authorization headers, or raw production responses.
- Production verification is read-only; do not publish a test comment.

---

### Task 1: Reproduce and classify the two production contract failures

**Files:**
- Create: `tests/integration/zentao/test_production_contract_shapes.py`
- Modify: none

**Interfaces:**
- Consumes: `DependencyFactory._production(Path)` and `HttpZentaoProvider` public query methods.
- Produces: sanitized evidence containing only operation name, exception class, HTTP status category, top-level key names, and nested collection type names.

- [ ] **Step 1: Add an opt-in diagnostic test**

```python
import os
from pathlib import Path

import pytest

from zentao_ai.cli.runtime import DependencyFactory


@pytest.mark.skipif(
    os.getenv("ZENTAO_PRODUCTION_CONTRACT_TEST") != "1",
    reason="production contract probe is opt-in",
)
def test_production_read_contracts_are_available() -> None:
    with DependencyFactory()(Path(r"F:\每日工作")) as runtime:
        page = runtime.provider.query_user_bugs("weiwenting", page=1, page_size=20)
        assert page.items
        history = runtime.provider.query_bug_history(page.items[0].id, page=1, page_size=20)
        assert history.coverage.total >= 0
```

- [ ] **Step 2: Run the diagnostic and verify the existing failure**

Run: `$env:ZENTAO_PRODUCTION_CONTRACT_TEST='1'; pytest tests/integration/zentao/test_production_contract_shapes.py -vv`

Expected before repair: FAIL with `ContractError` from `query_user_bugs` or `query_bug_history`; no credential value or raw payload appears.

- [ ] **Step 3: Record only sanitized contract shape at the failing boundary**

Temporarily run a local one-off probe that reports `response.status_code`, sorted top-level keys, and the Python type of `bugs`, `items`, `actions`, and `pager`; do not persist the response body. Remove the probe after the failing tests in Tasks 2 and 3 encode the observed shapes.

- [ ] **Step 4: Commit the opt-in reproduction**

```powershell
git add tests/integration/zentao/test_production_contract_shapes.py
git commit -m "test: reproduce Zentao production query contracts"
```

### Task 2: Repair arbitrary-assignee Bug querying

**Files:**
- Modify: `src/zentao_ai/zentao/http_provider.py:400-487`
- Modify: `tests/integration/zentao/test_http_provider.py:970-1280`

**Interfaces:**
- Consumes: `query_user_bugs(user: str, *, scope_names: tuple[str, ...] = (), page: int = 1, page_size: int = 20) -> BugPage`.
- Produces: `BugPage` containing only snapshots whose normalized assignee account equals the requested account, with `Coverage(total=-1, pages=None)` unless the full upstream collection was proven complete.

- [ ] **Step 1: Write a failing test for the official arbitrary-user response path**

```python
def test_query_user_bugs_filters_official_collection_by_assignee_account() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api.php/v2/bugs"
        return httpx.Response(200, json={
            "bugs": [
                {"id": 1, "status": "active", "title": "designer", "openedBy": {"account": "qa"}, "assignedTo": {"account": "xuli"}, "lastEditedDate": "2026-07-20 09:00:00"},
                {"id": 2, "status": "active", "title": "other", "openedBy": {"account": "qa"}, "assignedTo": {"account": "other"}, "lastEditedDate": "2026-07-20 09:01:00"},
            ],
            "page": 1, "limit": 20, "total": 2,
        })

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
        auth=ZentaoAuth(username="weiwenting", apiToken="token"),
    ).query_user_bugs("xuli")

    assert [item.id for item in result.items] == [1]
    assert result.items[0].assignee == "xuli"
```

- [ ] **Step 2: Run the test and verify RED**

Run: `pytest tests/integration/zentao/test_http_provider.py::test_query_user_bugs_filters_official_collection_by_assignee_account -vv`

Expected: FAIL because the implementation requests `/api/bugs/user/xuli` or stores a mapping string instead of the assignee account.

- [ ] **Step 3: Normalize actor/account values and use the configured official collection**

Add a focused helper:

```python
@classmethod
def _account(cls, value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("account")
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    text = str(value).strip()
    return text or None
```

Use `_account()` for `openedBy` and `assignedTo` in `_official_snapshot()`. For `userBugs == "/api.php/v2/bugs"`, request that path for every account using `page` and `limit`, parse the official `bugs` envelope, and retain only snapshots where `normalized_text(snapshot.assignee) == normalized_text(user)`. Do not call the nonexistent `/api/bugs/user/{user}` fallback.

- [ ] **Step 4: Add pagination and fail-closed regression cases**

Add tests proving mapping-valued accounts parse correctly, unknown envelopes still raise `query_user_bugs: invalid items`, stable versions remain mandatory, and a filtered collection never claims a trustworthy total unless the entire upstream page set is consumed.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `pytest tests/integration/zentao/test_http_provider.py -k "query_user_bugs or official_snapshot" -vv`

Expected: all selected tests PASS.

- [ ] **Step 6: Commit the query repair**

```powershell
git add src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py
git commit -m "fix: query Bugs by arbitrary assignee"
```

### Task 3: Repair structured Bug history parsing and runtime wiring

**Files:**
- Modify: `src/zentao_ai/zentao/http_provider.py:518-550`
- Modify: `src/zentao_ai/cli/runtime.py:138-170`
- Modify: `tests/integration/zentao/test_http_provider.py:90-130`
- Modify: `tests/e2e/cli/test_cli.py`

**Interfaces:**
- Consumes: `query_bug_history(bug_id: int | str, *, page: int = 1, page_size: int = 20) -> HistoryPage`.
- Produces: normalized `BugHistoryEntry` values from an `items` list or an official `actions` list/map; each entry preserves sanitized raw fields and normalized `id`, `action`, `actor`, `idempotencyKey`, and `contentHash`.

- [ ] **Step 1: Replace the unsupported-history test with failing official-envelope tests**

```python
def test_default_bug_history_adapts_actions_envelope() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/bugs/7/history"
        return httpx.Response(200, json={
            "actions": {"9": {"id": "9", "actor": "qa", "action": "commented", "comment": "checked"}},
            "pager": {"pageID": 1, "recPerPage": 20, "recTotal": 1, "pageTotal": 1},
        })

    instance = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(bugHistory="/api/bugs/{bug_id}/history"),
    )
    result = instance.query_bug_history(7)
    assert [(item.id, item.actor, item.action) for item in result.items] == [("9", "qa", "commented")]
    assert result.coverage.total == 1
```

- [ ] **Step 2: Run the history test and verify RED**

Run: `pytest tests/integration/zentao/test_http_provider.py::test_default_bug_history_adapts_actions_envelope -vv`

Expected: FAIL with `query_bug_history: invalid items`.

- [ ] **Step 3: Implement strict `items`/`actions` normalization**

In `query_bug_history`, accept `items` only through `_items()`. Otherwise require `actions` to be a list or mapping whose values are mappings; reject every other shape with `ContractError("query_bug_history: invalid items")`. Convert pager keys `pageID`, `recPerPage`, `recTotal`, and `pageTotal` before calling `_safe_query_coverage()`.

- [ ] **Step 4: Wire the structured read endpoint**

In `DependencyFactory._production`, set:

```python
bugHistory="/api/bugs/{bug_id}/history"
```

Keep comment and step endpoints unchanged. Add an e2e assertion that production runtime no longer constructs `ZentaoEndpoints(bugHistory=None)`.

- [ ] **Step 5: Add strict error regressions**

Add tests proving scalar `actions`, non-mapping action entries, contradictory pager metadata, and HTTP authentication/permission failures are not converted to empty history.

- [ ] **Step 6: Run focused history and CLI tests**

Run: `pytest tests/integration/zentao/test_http_provider.py -k "bug_history" -vv`

Run: `pytest tests/e2e/cli/test_cli.py -vv`

Expected: all selected tests PASS.

- [ ] **Step 7: Commit the history repair**

```powershell
git add src/zentao_ai/zentao/http_provider.py src/zentao_ai/cli/runtime.py tests/integration/zentao/test_http_provider.py tests/e2e/cli/test_cli.py
git commit -m "fix: support structured Zentao Bug history"
```

### Task 4: Enable gated comments in the project configuration

**Files:**
- Modify: `F:\每日工作\.codex\zentao-ai-bug.yaml`

**Interfaces:**
- Consumes: `permissions.commentEnabled: bool`.
- Produces: validated configuration with `commentEnabled: true`; all workflow safety checks remain unchanged.

- [ ] **Step 1: Change only the comment permission**

```yaml
permissions:
  codeWriteEnabled: true
  commentEnabled: true
  stepUpdateEnabled: false
```

- [ ] **Step 2: Validate the configuration**

Run: `zentao-ai-state validate-config --config "F:\每日工作\.codex\zentao-ai-bug.yaml"`

Expected: JSON contains `"valid":true`, no errors, and redacted configuration contains `"commentEnabled":true`.

- [ ] **Step 3: Do not commit the workspace-local configuration**

The `.codex` directory is local runtime state and remains untracked. Verify with `git -C "F:\每日工作" status --short -- .codex/zentao-ai-bug.yaml` and report the local modification explicitly.

### Task 5: Full verification, reinstall, and production read-only acceptance

**Files:**
- Modify: none beyond Tasks 1-4

**Interfaces:**
- Consumes: repaired source tree and validated project configuration.
- Produces: installed `zentao-ai-assistant` whose CLI and MCP expose the repaired read contracts.

- [ ] **Step 1: Run the full automated suite**

Run: `pytest -q`

Expected: exit code 0 and zero failures.

Run: `ruff check src tests`

Expected: exit code 0.

Run: `mypy src`

Expected: exit code 0.

- [ ] **Step 2: Reinstall from the repaired local source**

Run: `pipx install --force "C:\Users\wwtlove66\.codex\.tmp\marketplaces\zentao-team"`

Expected: `zentao-ai-assistant` installs successfully and exposes `zentao-ai`, `zentao-ai-state`, `zentao-ai-repository`, and `zentao-ai-render-report`.

- [ ] **Step 3: Verify the installed code identity**

Run: `zentao-ai --help`

Expected: exit code 0 with the `bugs`, `report`, and `mcp` commands.

- [ ] **Step 4: Run production read-only acceptance queries**

Run these four commands:

```powershell
zentao-ai bugs user xuli --project "F:\每日工作" --json
zentao-ai bugs user wangxiankun --project "F:\每日工作" --json
zentao-ai bugs user duweijie --project "F:\每日工作" --json
zentao-ai bugs user wuyuxuan --project "F:\每日工作" --json
```

Confirm every result is either a structured Bug page or an explicit identity/auth/permission error, never an unexplained `ContractError` and never a false zero. Verify each returned snapshot's assignee account before associating it with the corresponding Chinese display name.

Run the opt-in production contract test from Task 1 again:

```powershell
$env:ZENTAO_PRODUCTION_CONTRACT_TEST='1'
pytest tests/integration/zentao/test_production_contract_shapes.py -vv
```

Confirm Bug history is returned as structured entries without writing.

- [ ] **Step 5: Re-run the personal report without comment publication**

Run: `zentao-ai report personal --project "F:\每日工作" --json`

Expected: `query_bug_history: unsupported by official contract` is absent. Do not authorize or execute a comment merely as a smoke test.

- [ ] **Step 6: Inspect final changes and commit remaining source tests**

Run: `git diff --check` and `git status --short` in the source repository. Commit only intentional source/test changes; leave `.codex-marketplace-install.json` untouched.
