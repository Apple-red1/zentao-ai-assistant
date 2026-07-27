# ZenTao Bug Pagination Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Bug list pagination use ZenTao 21.7.8's `pageID` parameter so user and assignee queries include Bugs beyond the first page.

**Architecture:** Keep the existing `BugService` query pipeline and change only the page-number parameter at the Bug scope-list boundary. A paging-sensitive integration test will emulate ZenTao ignoring the legacy `page` parameter, proving the regression before the one-line production fix.

**Tech Stack:** Python 3.11+, pytest/pytest-asyncio, Pydantic, Ruff, mypy, pipx, ZenTao 21.7.8 API v2.

## Global Constraints

- Do not write or modify any ZenTao Bug during implementation or acceptance.
- Do not log or persist passwords, Tokens, Cookies, authorization headers, or complete real business responses.
- Do not change filtering, sorting, summaries, maximum-result handling, MCP tool contracts, Skill behavior, or Marketplace metadata.
- Limit production behavior changes to the Bug scope-list page-number parameter.
- The regression test must be observed failing before `src/zentao_ai/bugs.py` is changed.

---

### Task 1: Reproduce and fix Bug list pagination

**Files:**
- Modify: `tests/integration/test_bug_queries.py:3-69`
- Modify: `src/zentao_ai/bugs.py:244-284`

**Interfaces:**
- Consumes: `BugService.query_user_bugs(user: UserRef, filters: BugFilters | None) -> BugQueryResult` and `JsonClient.request_json(..., params=...)`.
- Produces: Bug list requests containing `pageID=<1-based page>` and no legacy `page` parameter.

- [ ] **Step 1: Write the paging-sensitive failing regression test**

Update the model import so the test can construct the resolved target user:

```python
from zentao_ai.models import BugFilters, Settings, UserRef, ZentaoSettings
```

Make the existing `FakeApi` emulate the real API's `pageID` contract while retaining its current pagination assertions:

```python
class FakeApi:
    def __init__(self) -> None:
        self.requested_pages: list[int] = []

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        **kwargs: object,
    ) -> dict[str, Any]:
        assert path == "/products/3/bugs"
        page = int((params or {}).get("pageID", 1))
        self.requested_pages.append(page)
        start = (page - 1) * 100 + 1
        return {
            "bugs": [
                {
                    "id": bug_id,
                    "title": f"Bug {bug_id}",
                    "status": "active",
                    "assignedTo": "me",
                    "severity": 1,
                    "pri": 2,
                    "product": 3,
                }
                for bug_id in range(start, start + 100)
            ],
            "pager": {"pageTotal": 4, "pageID": page},
        }
```

Add a dedicated fake below `FakeApi`. It deliberately defaults to page 1 when `pageID` is absent, matching the observed ZenTao behavior:

```python
class AssigneePaginationApi:
    def __init__(self) -> None:
        self.requested_params: list[dict[str, object]] = []

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        **kwargs: object,
    ) -> dict[str, Any]:
        assert path == "/products/2/bugs"
        request_params = dict(params or {})
        self.requested_params.append(request_params)
        page_id = int(request_params.get("pageID", 1))
        assigned_to = "another-user" if page_id == 1 else "xujiangshan"
        return {
            "bugs": [
                {
                    "id": 1000 + page_id,
                    "title": f"Page {page_id}",
                    "status": "active",
                    "assignedTo": assigned_to,
                    "severity": 3,
                    "pri": 3,
                    "product": 2,
                }
            ],
            "pager": {"pageTotal": 2, "pageID": page_id},
        }
```

Add the regression test after `test_query_reads_every_page_until_limit`:

```python
async def test_user_query_reads_later_pages_with_page_id() -> None:
    api = AssigneePaginationApi()
    service = BugService(api, settings())
    user = UserRef(
        id="15",
        account="xujiangshan",
        real_name="徐江珊",
        kind="inside",
    )

    result = await service.query_user_bugs(
        user,
        BugFilters(product_id=2, status="active", max_results=10),
    )

    assert [bug.id for bug in result.bugs] == [1002]
    assert [params["pageID"] for params in api.requested_params] == [1, 2]
    assert all("page" not in params for params in api.requested_params)
```

- [ ] **Step 2: Run the new test and verify RED**

Run:

```bash
../zentao-ai-venv/bin/python -m pytest tests/integration/test_bug_queries.py::test_user_query_reads_later_pages_with_page_id -v
```

Expected: FAIL at `assert [bug.id for bug in result.bugs] == [1002]` because the old implementation sends `page`, the fake repeats page 1, and the result is `[]`.

- [ ] **Step 3: Implement the minimal production fix**

In `BugService._read_scope`, replace only the page-number key:

```python
params={
    "browseType": "unresolved" if filters.status == "unresolved" else "all",
    "pageID": page,
    "recPerPage": self._settings.query.page_size,
},
```

- [ ] **Step 4: Run the targeted test and verify GREEN**

Run:

```bash
../zentao-ai-venv/bin/python -m pytest tests/integration/test_bug_queries.py::test_user_query_reads_later_pages_with_page_id -v
```

Expected: PASS; the fake records `pageID` values `[1, 2]` and returns Bug 1002 for `xujiangshan`.

- [ ] **Step 5: Run the complete Bug query integration file**

Run:

```bash
../zentao-ai-venv/bin/python -m pytest tests/integration/test_bug_queries.py -v
```

Expected: all tests PASS, including the existing 250-result pagination test with requested pages `[1, 2, 3]`.

- [ ] **Step 6: Run repository verification**

Run:

```bash
../zentao-ai-venv/bin/python -m pytest -v
../zentao-ai-venv/bin/python -m ruff check src tests
../zentao-ai-venv/bin/python -m mypy src
git diff --check
```

Expected: every command exits 0 with no test failures, lint errors, type errors, or whitespace errors.

- [ ] **Step 7: Review and commit the isolated fix**

Run:

```bash
git diff -- src/zentao_ai/bugs.py tests/integration/test_bug_queries.py
git status --short
git add src/zentao_ai/bugs.py tests/integration/test_bug_queries.py
git commit -m "fix: use pageID for Bug pagination"
```

Expected: the diff contains the paging-sensitive test and the one-key production change only; the commit succeeds.

---

### Task 2: Package, install, and verify the fix against the configured ZenTao

**Files:**
- Read: `pyproject.toml`
- Read: `plugins/zentao-ai-bug/.codex-plugin/plugin.json`
- Read: `plugins/zentao-ai-bug/.mcp.json`
- No source files are modified in this task.

**Interfaces:**
- Consumes: the committed `BugService` fix and the existing pipx/Codex installation.
- Produces: an updated local `zentao-ai` executable and a live read-only acceptance result containing Bugs 2769, 3221, and 3346 for `xujiangshan`.

- [ ] **Step 1: Build and validate the package artifacts**

Run:

```bash
../zentao-ai-venv/bin/python -m build
../zentao-ai-venv/bin/python -m twine check dist/*
../zentao-ai-venv/bin/python /Users/wang66/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/zentao-ai-bug
```

Expected: source/wheel builds complete, Twine reports both distributions `PASSED`, and plugin validation exits 0.

- [ ] **Step 2: Reinstall the local Python package with pipx**

Run from the repository root:

```bash
pipx install --force .
```

Expected: pipx reports `zentao-ai-assistant` installed and the `zentao-ai` application available. Marketplace metadata is not changed because the MCP command and plugin bundle are unchanged.

- [ ] **Step 3: Run local diagnostics**

Run:

```bash
zentao-ai doctor
```

Expected: required checks for configuration, credentials, login, API v2, personal Bug query, and MCP are `PASS`; no secret values appear.

- [ ] **Step 4: Run a read-only live acceptance query through the installed package**

Run:

```bash
ZENTAO_PIPX_VENV_ROOT="$(pipx environment --value PIPX_LOCAL_VENVS)"
"$ZENTAO_PIPX_VENV_ROOT/zentao-ai-assistant/bin/python" - <<'PY'
import asyncio
import json

from zentao_ai.bugs import BugService
from zentao_ai.client import ZentaoClient
from zentao_ai.config import load_settings
from zentao_ai.credentials import KeyringCredentialStore
from zentao_ai.models import BugFilters
from zentao_ai.users import UserDirectory


async def main() -> None:
    expected_ids = {2769, 3221, 3346}
    settings = load_settings()
    async with ZentaoClient(settings, KeyringCredentialStore()) as client:
        users = UserDirectory(client)
        user = await users.resolve("xujiangshan", kind="inside", force_refresh=True)
        result = await BugService(client, settings).query_user_bugs(
            user,
            BugFilters(status="active", max_results=5000, order_by="id"),
        )
    matches = [
        {
            "id": bug.id,
            "status": bug.status,
            "assigned_to": bug.assigned_to,
        }
        for bug in result.bugs
        if bug.id in expected_ids
    ]
    print(json.dumps({"matches": matches}, ensure_ascii=False))
    assert expected_ids <= {item["id"] for item in matches}
    assert all(item["status"] == "active" for item in matches)
    assert all(item["assigned_to"] == "xujiangshan" for item in matches)


asyncio.run(main())
PY
```

Expected: the command prints only the three non-secret field snapshots and exits 0; all expected IDs are present, active, and assigned to `xujiangshan`.

- [ ] **Step 5: Confirm repository state and hand off reload**

Run:

```bash
git status --short --branch
git log -3 --oneline
```

Expected: the working tree is clean and history contains the design, implementation-plan, and `fix: use pageID for Bug pagination` commits. Tell the user to start a new Codex task so the plugin launches a fresh MCP process from the updated executable.
