# Zentao Global Title Query Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a session-visible, assignee-independent Bug title search to the shared provider, MCP Server, CLI, and Codex plugin.

**Architecture:** Add one deterministic title normalizer in `zentao.query_filters`, one read-only `query_bugs_by_title` provider method that scans the official global Bug collection before applying result pagination, and thin MCP/CLI adapters that delegate to it. Reuse `BugPage` and existing coverage/error contracts so every surface reports unstable snapshots and incomplete scans consistently.

**Tech Stack:** Python 3.11+, httpx, Pydantic v2, Typer, MCP Python SDK, pytest, Ruff, mypy.

## Global Constraints

- `status` accepts only `unclosed` and `all`; the default is `unclosed`.
- Search accepts only a non-empty title keyword and does not add assignee, priority, scope, or query-DSL fields.
- Normalize with Unicode NFC and `casefold`, then remove Unicode whitespace and `【】[]（）()-—_:：/` before continuous-substring matching.
- Query only Bugs visible to the current Zentao session; do not use `personal.scopeNames`, `team.scopeNames`, or `team.members`.
- Preserve `BugPage`, `BugSnapshot`, `Coverage`, `ItemFailure`, `version=v1`, unstable-snapshot, missing-presentation-field, and conservative-pagination contracts.
- The new capability is read-only and must not call comments, step updates, repair workflows, Bug state changes, repository operations, or report generation.
- Do not expose delete, assign, resolve, close, activate, convert, or another write-equivalent tool.
- Follow test-driven development: every production change follows a focused failing test that is observed failing for the expected reason.

---

### Task 1: Shared title matching semantics

**Files:**
- Modify: `src/zentao_ai/zentao/query_filters.py`
- Modify: `tests/unit/zentao/test_query_filters.py`

**Interfaces:**
- Consumes: `BugSnapshot.title`, `BugSnapshot.status`, existing `is_unclosed_status(status: str) -> bool`.
- Produces: `normalize_title_search_text(value: str) -> str`, `filter_title_bugs(items, *, title_keyword, status) -> tuple[BugSnapshot, ...]`.

- [ ] **Step 1: Write failing matcher tests**

Append tests that express the screenshot cases, continuous phrase, case folding, and negative ordering:

```python
import pytest

from zentao_ai.zentao.query_filters import filter_title_bugs


@pytest.mark.parametrize(
    "title",
    [
        "【设计器】【统一面板-文本元素】文本元素悬停设置宽度未生效",
        "【设计器】【统一面板-time】字体大小设置H标签的字体大小时未生效",
        "【设计器】【统一面板-按钮】按钮元素中字体颜色未生效",
        "【设计器】【统一面板-倒计时】选中其中一个part会跳到不存在的part中",
        "【设计器】【统一面板-容器类】设置视频背景后无法调节透明度",
        "【AI建站】设计器统一面板样式异常",
    ],
)
def test_title_keyword_matches_across_supported_separators(title: str) -> None:
    item = BugSnapshot(id=1, title=title, status="active", snapshotVersion="v1")
    assert filter_title_bugs(
        (item,), title_keyword="设计器统一面板", status="unclosed"
    ) == (item,)


def test_title_keyword_uses_nfc_casefold_and_continuous_order() -> None:
    matching = BugSnapshot(
        id=1, title="【DESIGNER】 Cafe\u0301-Panel", status="open", snapshotVersion="v1"
    )
    reordered = BugSnapshot(
        id=2, title="Panel Designer Café", status="open", snapshotVersion="v2"
    )
    assert filter_title_bugs(
        (matching, reordered), title_keyword="designer cafépanel", status="unclosed"
    ) == (matching,)


def test_title_keyword_rejects_empty_after_normalization() -> None:
    with pytest.raises(ValueError, match="title keyword is empty"):
        filter_title_bugs((), title_keyword="【】- : /", status="unclosed")


def test_title_keyword_defaults_are_enforced_by_callers_and_status_filters() -> None:
    active = BugSnapshot(id=1, title="设计器统一面板", status="active", snapshotVersion="v1")
    closed = BugSnapshot(id=2, title="设计器统一面板", status="closed", snapshotVersion="v2")
    assert filter_title_bugs(
        (active, closed), title_keyword="设计器统一面板", status="unclosed"
    ) == (active,)
    assert filter_title_bugs(
        (active, closed), title_keyword="设计器统一面板", status="all"
    ) == (active, closed)
```

- [ ] **Step 2: Run the matcher tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/zentao/test_query_filters.py -q
```

Expected: collection fails because `filter_title_bugs` does not exist.

- [ ] **Step 3: Implement the minimal shared matcher**

Add the supported separator set and functions to `query_filters.py`:

```python
_TITLE_SEARCH_SEPARATORS = frozenset("【】[]（）()-—_:：/")


def normalize_title_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip().casefold()
    return "".join(
        char
        for char in normalized
        if not char.isspace() and char not in _TITLE_SEARCH_SEPARATORS
    )


def filter_title_bugs(
    items: tuple[BugSnapshot, ...],
    *,
    title_keyword: str,
    status: Literal["all", "unclosed"],
) -> tuple[BugSnapshot, ...]:
    keyword = normalize_title_search_text(title_keyword)
    if not keyword:
        raise ValueError("title keyword is empty")
    return tuple(
        item
        for item in items
        if keyword in normalize_title_search_text(item.title)
        and (status == "all" or is_unclosed_status(item.status))
    )
```

- [ ] **Step 4: Run focused and existing filter tests and verify GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/zentao/test_query_filters.py -q
```

Expected: all query-filter tests pass.

- [ ] **Step 5: Commit the matcher**

```powershell
git add src/zentao_ai/zentao/query_filters.py tests/unit/zentao/test_query_filters.py
git commit -m "feat: add normalized Bug title matching"
```

### Task 2: Provider global collection query

**Files:**
- Modify: `src/zentao_ai/zentao/provider.py`
- Modify: `src/zentao_ai/zentao/models.py`
- Modify: `src/zentao_ai/zentao/http_provider.py`
- Modify: `tests/integration/zentao/test_http_provider.py`

**Interfaces:**
- Consumes: `filter_title_bugs`, existing `_request`, `_official_bug_rows`, `_snapshot_or_failure`, `_official_page_metadata`, `missing_presentation_field_counts`.
- Produces: `ZentaoProvider.query_bugs_by_title(title_keyword, *, status="unclosed", page=1, page_size=20) -> BugPage` and the matching `HttpZentaoProvider` implementation.

- [ ] **Step 1: Write failing provider tests for global scope and filtered pagination**

Add tests with a two-page `httpx.MockTransport`. The handler must assert every request uses `/api.php/v2/bugs`, `browseType=all`, and never sends `user`, `assignedTo`, `scopeNames`, or a member identity. Page one returns a nonmatching Bug and one matching active Bug; page two returns one matching closed Bug and one matching active Bug.

```python
def test_query_bugs_by_title_scans_global_collection_before_result_paging() -> None:
    requests: list[httpx.Request] = []

    def row(identifier: int, title: str, status: str) -> dict[str, object]:
        return {
            "id": identifier,
            "title": title,
            "status": status,
            "pri": 3,
            "openedBy": "qa",
            "assignedTo": "developer",
            "lastEditedDate": f"2026-07-23 10:{identifier:02d}:00",
        }

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == "/api.php/v2/bugs"
        assert request.url.params["browseType"] == "all"
        assert not ({"user", "assignedTo", "scopeNames"} & set(request.url.params))
        page = int(request.url.params["pageID"])
        rows = {
            1: [
                row(1, "unrelated", "active"),
                row(2, "【设计器】【统一面板-文本元素】宽度未生效", "active"),
            ],
            2: [
                row(3, "【AI建站】设计器统一面板旧问题", "closed"),
                row(4, "【AI建站】设计器统一面板样式异常", "active"),
            ],
        }[page]
        return httpx.Response(
            200,
            json={"bugs": rows, "pager": {"pageID": page, "recPerPage": 2, "recTotal": 4, "pageTotal": 2}},
        )

    result = provider(httpx.MockTransport(handle)).query_bugs_by_title(
        "设计器统一面板", page=2, page_size=1
    )
    assert [item.id for item in result.items] == [4]
    assert result.coverage.model_dump() == {
        "page": 2,
        "pageSize": 1,
        "total": 2,
        "pages": 2,
        "returned": 1,
        "failed": 0,
        "complete": True,
        "unstableSnapshots": 0,
        "missingPresentationFields": {},
    }
    assert len(requests) == 2


def test_query_bugs_by_title_all_includes_closed_matches() -> None:
    def handle(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {"id": 2, "title": "设计器统一面板新问题", "status": "active", "assignedTo": "alice", "lastEditedDate": "2026-07-23 10:02:00"},
                    {"id": 3, "title": "设计器统一面板旧问题", "status": "closed", "assignedTo": "bob", "lastEditedDate": "2026-07-23 10:03:00"},
                ],
                "pager": {"pageID": 1, "recPerPage": 20, "recTotal": 2, "pageTotal": 1},
            },
        )

    instance = provider(httpx.MockTransport(handle))
    assert [item.id for item in instance.query_bugs_by_title("设计器统一面板").items] == [2]
    assert [item.id for item in instance.query_bugs_by_title("设计器统一面板", status="all").items] == [2, 3]
```

- [ ] **Step 2: Run the new provider tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/zentao/test_http_provider.py -k "query_bugs_by_title" -q
```

Expected: failures state that `HttpZentaoProvider` has no `query_bugs_by_title` method.

- [ ] **Step 3: Add the protocol method and official global scan**

Add `Literal` to `provider.py` and the exact protocol signature:

```python
def query_bugs_by_title(
    self,
    title_keyword: str,
    *,
    status: Literal["all", "unclosed"] = "unclosed",
    page: int = 1,
    page_size: int = 20,
) -> BugPage: ...
```

Add a dedicated endpoint to `ZentaoEndpoints` in `models.py` so global querying does not overload the user-query endpoint:

```python
global_bugs: str = Field("/api.php/v2/bugs", alias="globalBugs")
```

In `HttpZentaoProvider`, validate pagination with `_validate_pagination`, validate the keyword by calling `normalize_title_search_text`, and request `self._endpoints.global_bugs`. Scan upstream pages with `browseType=all`, using the same duplicate-page, repeated-ID, pager-consistency, maximum-page, snapshot-or-failure, and conservative-completeness rules already used by `_query_official_user_bugs`. Do not call `_resolve_member_identity` and return `resolvedIdentity=None`.

After the scan, filter successful snapshots with:

```python
matched_items = filter_title_bugs(
    tuple(item for item in outcomes if isinstance(item, BugSnapshot)),
    title_keyword=title_keyword,
    status=status,
)
```

Keep matching `ItemFailure` records only when their title could be read and matched; failures without a trustworthy title cannot be claimed as matches and must make the scan incomplete. Apply `start = (page - 1) * page_size` and `end = start + page_size` to the filtered outcome sequence. Build coverage with filtered `total/pages` only when the upstream scan is complete; otherwise use `total=-1`, `pages=None`, and `complete=False`.

- [ ] **Step 4: Add conservative-pagination and unstable-row tests**

Add focused cases that assert:

```python
assert partial.coverage.complete is False
assert partial.coverage.total == -1
assert partial.coverage.pages is None
assert partial.items[0].snapshot_stable is False
assert partial.items[0].snapshot_version is None
```

The mock responses must separately cover repeated pages, cross-page duplicate IDs, contradictory pager values, and a matching versionless row. Add a test that passes `title_keyword="【】-:/"` and asserts the handler is never called.

- [ ] **Step 5: Run provider integration tests and verify GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/zentao/test_http_provider.py -k "query_bugs_by_title or query_user_bugs" -q
```

Expected: all selected provider tests pass, proving the new global scan did not change user-query behavior.

- [ ] **Step 6: Commit the provider capability**

```powershell
git add src/zentao_ai/zentao/provider.py src/zentao_ai/zentao/models.py src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py
git commit -m "feat: query visible Bugs by title"
```

### Task 3: MCP read-only tool

**Files:**
- Modify: `src/zentao_ai/mcp_server/schemas.py`
- Modify: `src/zentao_ai/mcp_server/tools.py`
- Modify: `tests/contract/test_mcp_tools.py`
- Modify: `tests/e2e/test_mcp_stdio.py`

**Interfaces:**
- Consumes: `ZentaoProvider.query_bugs_by_title(...) -> BugPage` from Task 2.
- Produces: strict `QueryBugsByTitleInput` and MCP tool `query_bugs_by_title` returning `{"version": "v1", "data": BugPage}`.

- [ ] **Step 1: Write failing MCP schema and dispatch tests**

Add `QueryBugsByTitleInput` imports and tests:

```python
def test_query_bugs_by_title_schema_defaults_and_rejects_unknown_fields() -> None:
    value = QueryBugsByTitleInput.model_validate({"titleKeyword": "设计器统一面板"})
    assert value.status == "unclosed"
    assert value.page == 1
    assert value.pageSize == 20
    with pytest.raises(ValidationError):
        QueryBugsByTitleInput.model_validate({"titleKeyword": " ", "user": "alice"})


def test_query_bugs_by_title_dispatches_without_identity_or_scope() -> None:
    provider = Provider()
    result = ZentaoTools(runtime(provider)).call(
        "query_bugs_by_title",
        {"titleKeyword": "设计器统一面板", "status": "unclosed", "page": 2, "pageSize": 50},
    )
    assert result["version"] == "v1"
    assert provider.calls == [("title", "设计器统一面板", {"status": "unclosed", "page": 2, "page_size": 50})]
```

Extend the test `Provider` with a `query_bugs_by_title` recording stub, and update the exact `TOOL_NAMES` assertion to include the new read-only tool after `query_user_bugs`.

- [ ] **Step 2: Run MCP contract tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/contract/test_mcp_tools.py tests/e2e/test_mcp_stdio.py -q
```

Expected: import/tool-list/dispatch failures because the schema and tool are absent.

- [ ] **Step 3: Implement strict MCP input and dispatch**

Add to `schemas.py`:

```python
class QueryBugsByTitleInput(PagingInput):
    titleKeyword: NonEmpty
    status: Literal["all", "unclosed"] = "unclosed"
```

Register it in `INPUT_MODELS`. Add `query_bugs_by_title` to `TOOL_NAMES`, import the input class in `tools.py`, and dispatch directly:

```python
elif name == "query_bugs_by_title":
    assert isinstance(value, QueryBugsByTitleInput)
    data = provider.query_bugs_by_title(
        value.titleKeyword,
        status=value.status,
        page=value.page,
        page_size=value.pageSize,
    )
```

Do not route through team membership, personal account, reports, or `_filtered_assignee_page`.

- [ ] **Step 4: Run MCP tests and verify GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/contract/test_mcp_tools.py tests/e2e/test_mcp_stdio.py -q
```

Expected: both suites pass and stdio tool discovery exposes `query_bugs_by_title`.

- [ ] **Step 5: Commit the MCP tool**

```powershell
git add src/zentao_ai/mcp_server/schemas.py src/zentao_ai/mcp_server/tools.py tests/contract/test_mcp_tools.py tests/e2e/test_mcp_stdio.py
git commit -m "feat: expose global title query over MCP"
```

### Task 4: CLI search command

**Files:**
- Modify: `src/zentao_ai/cli/bug_commands.py`
- Modify: `tests/e2e/cli/test_cli.py`
- Modify: `tests/e2e/test_workflow_parity.py`

**Interfaces:**
- Consumes: `ZentaoProvider.query_bugs_by_title(...) -> BugPage` from Task 2 and existing `render_bug_table`/`_emit` output paths.
- Produces: `zentao-ai bugs search --title TEXT [--status unclosed|all] [--page N] [--page-size N] [--json]`.

- [ ] **Step 1: Write failing CLI tests**

Extend the CLI test provider with the same recording method and add:

```python
def test_bugs_search_defaults_to_unclosed_and_renders_table(tmp_path: Path) -> None:
    provider = Provider()
    result = CliRunner().invoke(
        app,
        ["bugs", "search", "--title", "设计器统一面板"],
        obj=factory(tmp_path, provider=provider),
    )
    assert result.exit_code == 0
    assert "| Bug号 | 标题 | 优先级 | 状态 | 负责人 | 快照稳定性 |" in result.stdout
    assert provider.calls == [("title", "设计器统一面板", "unclosed", 1, 20)]


def test_bugs_search_passes_all_status_paging_and_json(tmp_path: Path) -> None:
    provider = Provider()
    result = CliRunner().invoke(
        app,
        ["bugs", "search", "--title", "设计器统一面板", "--status", "all", "--page", "2", "--page-size", "50", "--json"],
        obj=factory(tmp_path, provider=provider),
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["ok"] is True
    assert provider.calls == [("title", "设计器统一面板", "all", 2, 50)]
```

Add a parity test that calls MCP and CLI with the same fake Provider page and asserts equal `items`, `coverage`, and `itemFailures`.

- [ ] **Step 2: Run CLI tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/e2e/cli/test_cli.py tests/e2e/test_workflow_parity.py -k "bugs_search or title_query" -q
```

Expected: Typer reports that `search` is not a known `bugs` command.

- [ ] **Step 3: Implement the thin CLI command**

Add to `bug_commands.py`:

```python
@bugs_app.command("search")
@guarded
def search(
    ctx: typer.Context,
    title: str = typer.Option(..., "--title"),
    status: Literal["all", "unclosed"] = typer.Option("unclosed", "--status"),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(20, "--page-size", min=1, max=100),
    project: Path = typer.Option(Path.cwd()),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    with _runtime(ctx, project) as runtime:
        result = runtime.provider.query_bugs_by_title(
            title,
            status=status,
            page=page,
            page_size=page_size,
        )
        if json_output:
            _emit(result, True)
        else:
            typer.echo(render_bug_table(result))
```

Provider validation remains authoritative for keywords that normalize to empty; `@guarded` must redact the error and return the existing business exit code.

- [ ] **Step 4: Run CLI and parity tests and verify GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/e2e/cli/test_cli.py tests/e2e/test_workflow_parity.py -q
```

Expected: both suites pass with identical MCP/CLI structured output for identical Provider results.

- [ ] **Step 5: Commit the CLI command**

```powershell
git add src/zentao_ai/cli/bug_commands.py tests/e2e/cli/test_cli.py tests/e2e/test_workflow_parity.py
git commit -m "feat: add CLI Bug title search"
```

### Task 5: Codex plugin contract and user documentation

**Files:**
- Modify: `plugins/zentao-ai-bug/skills/zentao-ai-bug/SKILL.md`
- Modify: `plugins/zentao-ai-bug/skills/zentao-ai-bug/personal-bug-agent.md`
- Modify: `README.md`
- Modify: `tests/contract/test_plugin_package.py`
- Modify: `tests/contract/test_legacy_feature_inventory.py`

**Interfaces:**
- Consumes: MCP tool `query_bugs_by_title` and CLI command from Tasks 3–4.
- Produces: documented intent routing for unrestricted session-visible title searches without granting write or report permissions.

- [ ] **Step 1: Write failing plugin contract tests**

Add assertions that the Skill names the tool, default state, matching semantics, and read-only boundary:

```python
def test_skill_documents_global_title_query_as_session_visible_read_only() -> None:
    text = (PLUGIN / "skills" / "zentao-ai-bug" / "SKILL.md").read_text(encoding="utf-8")
    assert "query_bugs_by_title" in text
    assert "默认" in text and "unclosed" in text
    assert "不限定负责人" in text
    assert "不得转入个人或团队日报" in text
```

Update the legacy feature inventory with one entry requiring `query_bugs_by_title`, `titleKeyword`, `status=unclosed`, and `只读`.

- [ ] **Step 2: Run plugin contract tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/contract/test_plugin_package.py tests/contract/test_legacy_feature_inventory.py -q
```

Expected: the new assertions fail because the tool is not documented.

- [ ] **Step 3: Update Skill and README contracts**

Add `query_bugs_by_title` to the read-only allowlist and document:

```text
全局标题临时查询使用 query_bugs_by_title；titleKeyword 为必填非空关键词，status 默认 unclosed，只有用户明确要求其他状态时才传 all。查询不限定负责人，不应用个人/团队范围，仅受当前禅道会话权限约束，不得转入个人或团队日报，也不得触发评论、代码或 Bug 状态副作用。标题匹配在 Unicode NFC/casefold 后忽略空白及 【】[]（）()-—_:：/，再执行顺序连续子串匹配。
```

Add the CLI examples to `README.md`:

```text
zentao-ai bugs search --title "设计器统一面板"
zentao-ai bugs search --title "设计器统一面板" --status all --json
```

- [ ] **Step 4: Run plugin contracts and verify GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/contract/test_plugin_package.py tests/contract/test_legacy_feature_inventory.py -q
```

Expected: all selected contract tests pass and no write allowlist changes are required.

- [ ] **Step 5: Commit plugin documentation**

```powershell
git add plugins/zentao-ai-bug/skills/zentao-ai-bug/SKILL.md plugins/zentao-ai-bug/skills/zentao-ai-bug/personal-bug-agent.md README.md tests/contract/test_plugin_package.py tests/contract/test_legacy_feature_inventory.py
git commit -m "docs: teach plugin global Bug title search"
```

### Task 6: Full verification and package smoke test

**Files:**
- Modify only if a verification failure demonstrates an in-scope defect in files already listed above.

**Interfaces:**
- Consumes: completed Tasks 1–5.
- Produces: passing unit, integration, contract, end-to-end, type, lint, and packaging evidence.

- [ ] **Step 1: Run all automated tests**

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Expected: the complete test suite passes with no failures.

- [ ] **Step 2: Run static checks**

```powershell
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src
```

Expected: both commands exit 0 with no diagnostics.

- [ ] **Step 3: Run CLI and MCP package smoke checks**

```powershell
.venv\Scripts\zentao-ai.exe bugs search --help
.venv\Scripts\python.exe -m pytest tests/contract/test_plugin_package.py tests/e2e/test_mcp_stdio.py -q
```

Expected: help lists `--title`, `--status`, `--page`, `--page-size`, and `--json`; package/MCP tests pass.

- [ ] **Step 4: Inspect the final diff and safety surface**

```powershell
git diff --check HEAD~5..HEAD
git diff --stat HEAD~5..HEAD
rg -n "delete_bug|remove_bug|assign_bug|resolve_bug|close_bug|activate_bug" src/zentao_ai/mcp_server plugins/zentao-ai-bug
```

Expected: no whitespace errors; changes are confined to the planned provider/MCP/CLI/Skill/test files; no destructive tool was added.

- [ ] **Step 5: Confirm the worktree contains no uncommitted implementation changes**

```powershell
git status --short
```

Expected: no output. If verification reveals an in-scope defect, stop this verification task, create a focused failing regression test in the owning task's listed test file, implement the minimal correction in that task's listed production file, rerun the full verification sequence, and commit those two exact files with `fix: close global title query verification gap`.
