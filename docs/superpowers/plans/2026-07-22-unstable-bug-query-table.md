# Unstable Bug Query Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve versionless Zentao Bug rows with explicit instability metadata, render ad-hoc CLI queries as Markdown tables, and permit comments or local repair only with exact current-turn authorization for the concrete Bug and action.

**Architecture:** Normalize stable and unstable Bug rows into one `BugSnapshot` model instead of converting missing versions into item failures. MCP serialization remains structured and lossless, while the CLI adds a dedicated table renderer. Authorization treats an unstable snapshot as a protected condition: exact authorization permits entry into existing comment or repair gates, and a fresh re-query must match the available safety fields before a side effect.

**Tech Stack:** Python 3.12+, Pydantic, Typer, httpx, pytest, Ruff, mypy.

## Global Constraints

- Never synthesize a stable version from mutable display fields.
- Versionless rows use `snapshotVersion=null` and `snapshotStable=false`.
- The minimum visible fields are Bug ID, title, priority, status, assignee, and snapshot stability.
- Missing visible fields render as `unknown` and do not remove the row.
- Unstable-snapshot comments and local repairs require exact current-turn authorization for one Bug and one action.
- Exact authorization does not bypass history, cooldown, idempotency, routing, repository, test, diff, or final review gates.
- Resolving, closing, assigning, activating, deleting, committing, pushing, merging, and deploying are not broadened.
- Permanent Bug deletion remains unconditionally forbidden.

## File Structure

- `src/zentao_ai/zentao/models.py`: normalized Bug and coverage/degradation types.
- `src/zentao_ai/zentao/http_provider.py`: stable/unstable row normalization and fresh detail retrieval.
- `src/zentao_ai/mcp_server/tools.py`: structured MCP propagation without losing degradation metadata.
- `src/zentao_ai/cli/bug_table.py`: focused Markdown table escaping and rendering.
- `src/zentao_ai/cli/bug_commands.py`: CLI selection between table and JSON output.
- `src/zentao_ai/safety/actions.py`: authorization context flag for unstable snapshots.
- `src/zentao_ai/safety/authorization.py`: exact-authorization rule for unstable comments and writes.
- `src/zentao_ai/workflows/snapshot_guard.py`: pre-side-effect comparison of unstable snapshots.
- `src/zentao_ai/workflows/comments.py` and `src/zentao_ai/workflows/repair.py`: invoke fresh-snapshot guard before side effects.
- Existing provider, MCP, CLI, safety, and workflow tests: regression coverage.

---

### Task 1: Model Degraded Bug Snapshots

**Files:**
- Modify: `src/zentao_ai/zentao/models.py`
- Test: `tests/unit/zentao/test_models.py`

**Interfaces:**
- Produces: `BugSnapshot.version: str | None`, `BugSnapshot.snapshot_version: str | None`, `BugSnapshot.snapshot_stable: bool`, `BugSnapshot.priority: str`, and `Coverage.unstable_snapshots: int`.
- Consumes: existing Pydantic alias conventions and immutable `FrozenModel` behavior.

- [ ] **Step 1: Write failing model tests**

```python
def test_bug_snapshot_accepts_explicit_unstable_versionless_row():
    bug = BugSnapshot.model_validate({
        "id": 3422,
        "title": "SEO Rule-twitter",
        "priority": "P3",
        "status": "active",
        "assignee": "zhouhaiyin",
        "version": None,
        "snapshotVersion": None,
        "snapshotStable": False,
    })
    assert bug.snapshot_version is None
    assert bug.snapshot_stable is False
    assert bug.priority == "P3"


def test_stable_snapshot_requires_matching_nonempty_version():
    with pytest.raises(ValueError, match="stable snapshot requires version"):
        BugSnapshot(id=1, status="active", version=None,
                    snapshotVersion=None, snapshotStable=True)
```

- [ ] **Step 2: Run the model tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/zentao/test_models.py -q`

Expected: FAIL because `version` is required and `snapshotStable`/`priority` are not modeled.

- [ ] **Step 3: Implement the minimal normalized fields and invariant**

```python
class BugSnapshot(FrozenModel):
    id: int | str
    status: str = "unknown"
    creator: CreatorAccount | None = None
    assignee: str | None = None
    version: str | None = None
    snapshot_version: str | None = Field(None, alias="snapshotVersion")
    snapshot_stable: bool = Field(False, alias="snapshotStable")
    title: str = "unknown"
    priority: str = "unknown"
    steps: str = ""
    routing: RoutingData | None = None
    raw: Mapping[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_snapshot_stability(self) -> Self:
        if self.snapshot_stable and not (self.version and self.snapshot_version):
            raise ValueError("stable snapshot requires version")
        return self


class Coverage(FrozenModel):
    # existing fields remain unchanged
    unstable_snapshots: int = Field(0, alias="unstableSnapshots")
```

Update stable test fixtures to pass `snapshotStable=True`; keep transport placeholders explicitly stable.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/zentao/test_models.py tests/unit/zentao/test_query_filters.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/zentao_ai/zentao/models.py tests/unit/zentao/test_models.py tests/unit/zentao/test_query_filters.py
git commit -m "feat: model unstable bug snapshots"
```

### Task 2: Retain Versionless Rows in the HTTP Provider

**Files:**
- Modify: `src/zentao_ai/zentao/http_provider.py`
- Test: `tests/integration/zentao/test_http_provider.py`
- Test: `tests/integration/zentao/test_production_contract_shapes.py`

**Interfaces:**
- Consumes: the Task 1 `BugSnapshot` and `Coverage.unstable_snapshots` fields.
- Produces: `_official_snapshot(data, operation, allow_unstable=False) -> BugSnapshot` and `query_bug_detail(bug_id, *, allow_unstable=False) -> BugSnapshot`; list queries normalize with `allow_unstable=True`, while unstable comment/repair preflight explicitly calls detail with `allow_unstable=True`.

- [ ] **Step 1: Replace the old missing-version regression expectation with a failing retention test**

```python
def test_query_user_bugs_retains_official_bug_without_stable_version() -> None:
    # Reuse the existing official-list transport fixture for Bug 2537.
    result = provider(
        transport, endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs")
    ).query_user_bugs("alice")

    assert [(item.id, item.title, item.priority, item.status) for item in result.items] == [
        (2537, "【AI建站】Missing version", "P3", "active")
    ]
    assert result.items[0].snapshot_version is None
    assert result.items[0].snapshot_stable is False
    assert result.coverage.unstable_snapshots == 1
    assert result.item_failures == ()
```

Add a second test where `title`, `pri`, and `assignedTo` are missing; assert the row remains and normalized presentation fields are `unknown`/`None`.

- [ ] **Step 2: Run the provider tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/integration/zentao/test_http_provider.py -k "without_stable_version or missing_presentation" -q`

Expected: FAIL because the provider currently emits `MISSING_STABLE_VERSION` and drops the item.

- [ ] **Step 3: Implement degraded normalization**

```python
def _priority(self, data: Mapping[str, Any]) -> str:
    value = data.get("pri", data.get("priority"))
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return "unknown"
    normalized = str(value).strip()
    return f"P{normalized}" if normalized.isdigit() else (normalized or "unknown")


def _official_snapshot(
    self, data: Mapping[str, Any], operation: str = "query_my_bugs",
    *, allow_unstable: bool = False,
) -> BugSnapshot:
    raw_version = data.get("lastEditedDate") or data.get("version")
    version = str(raw_version).strip() if isinstance(raw_version, (str, int)) else None
    if not version and not allow_unstable:
        raise MissingStableVersionError(f"{operation}: missing stable version")
    normalized = {
        "id": data.get("id"),
        "status": self._catalog_text(data.get("status")) or "unknown",
        "title": self._catalog_text(data.get("title")) or "unknown",
        "priority": self._priority(data),
        "creator": self._account(data.get("openedBy")),
        "assignee": self._account(data.get("assignedTo")),
        "version": version,
        "snapshotVersion": version,
        "snapshotStable": version is not None,
        "steps": data.get("steps", ""),
        "raw": self._sanitize(data),
    }
    return self._with_routing(BugSnapshot.model_validate(normalized))
```

Call the normalizer with `allow_unstable=True` for user-list rows and count unstable returned items when constructing `Coverage`. Keep invalid IDs as item failures.

Extend `query_bug_detail` with the keyword-only `allow_unstable` parameter and pass it to the same normalizer. Update the `Provider` protocol and test doubles with the defaulted keyword so existing callers remain strict and compatible.

- [ ] **Step 4: Run provider and production-shape tests**

Run: `.venv\Scripts\python.exe -m pytest tests/integration/zentao/test_http_provider.py tests/integration/zentao/test_production_contract_shapes.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py tests/integration/zentao/test_production_contract_shapes.py
git commit -m "fix: retain versionless bug query rows"
```

### Task 3: Propagate Degraded Rows Through MCP

**Files:**
- Modify: `src/zentao_ai/mcp_server/tools.py`
- Test: `tests/contract/test_mcp_tools.py`
- Test: `tests/e2e/test_mcp_stdio.py`

**Interfaces:**
- Consumes: `BugPage` containing stable and unstable items.
- Produces: `query_user_bugs` structured content with unchanged item order and aliases `snapshotVersion`, `snapshotStable`, `priority`, and `coverage.unstableSnapshots`.

- [ ] **Step 1: Write a failing MCP contract test**

```python
def test_session_visible_mcp_keeps_unstable_rows_with_display_fields(runtime):
    runtime.provider.query_user_bugs.return_value = BugPage(
        items=(BugSnapshot(
            id=3422, title="SEO Rule-twitter", priority="P3", status="active",
            assignee="zhouhaiyin", version=None, snapshotVersion=None,
            snapshotStable=False,
        ),),
        coverage=Coverage(total=1, pages=1, returned=1,
                          complete=True, unstableSnapshots=1),
    )
    payload = ZentaoTools(runtime).call("query_user_bugs", {
        "user": "周海音", "status": "unclosed", "scopeMode": "session-visible"
    })
    row = payload["data"]["items"][0]
    assert row["id"] == 3422
    assert row["title"] == "SEO Rule-twitter"
    assert row["priority"] == "P3"
    assert row["status"] == "active"
    assert row["snapshotVersion"] is None
    assert row["snapshotStable"] is False
```

- [ ] **Step 2: Run MCP tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/contract/test_mcp_tools.py tests/e2e/test_mcp_stdio.py -k unstable -q`

Expected: FAIL until the aliases and coverage metadata survive filtering and serialization.

- [ ] **Step 3: Preserve degradation metadata when rebuilding filtered pages**

In both `_filtered_assignee_page` implementations, copy the new coverage field:

```python
Coverage(
    page=page,
    pageSize=page_size,
    total=len(items) if complete else -1,
    pages=(0 if not items else 1) if complete else None,
    returned=len(items),
    failed=coverage.failed,
    complete=complete,
    unstableSnapshots=sum(not item.snapshot_stable for item in items),
)
```

Do not create item failures solely for unstable rows.

- [ ] **Step 4: Run MCP tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/contract/test_mcp_tools.py tests/e2e/test_mcp_stdio.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/zentao_ai/mcp_server/tools.py tests/contract/test_mcp_tools.py tests/e2e/test_mcp_stdio.py
git commit -m "feat: expose unstable bug rows through mcp"
```

### Task 4: Render CLI User Queries as Markdown Tables

**Files:**
- Create: `src/zentao_ai/cli/bug_table.py`
- Modify: `src/zentao_ai/cli/bug_commands.py`
- Test: `tests/e2e/cli/test_cli.py`

**Interfaces:**
- Consumes: `BugPage` from Tasks 1–3.
- Produces: `render_bug_table(page: BugPage) -> str`.
- Preserves: `--json` output remains the structured success envelope.

- [ ] **Step 1: Write failing CLI table tests**

```python
def test_bugs_user_renders_markdown_table_with_unstable_row(tmp_path):
    provider = Provider()
    provider.user_page = BugPage(
        items=(BugSnapshot(
            id=3422, title="SEO | Rule\nTwitter", priority="P3",
            status="active", assignee="zhouhaiyin", version=None,
            snapshotVersion=None, snapshotStable=False,
        ),),
        coverage=Coverage(total=1, pages=1, returned=1,
                          complete=True, unstableSnapshots=1),
    )
    result = CliRunner().invoke(
        app, ["bugs", "user", "周海音", "--scope-mode", "session-visible",
              "--status", "unclosed"],
        obj=factory(tmp_path, provider=provider),
    )
    assert result.exit_code == 0
    assert "| Bug号 | 标题 | 优先级 | 状态 | 负责人 | 快照稳定性 |" in result.stdout
    assert "| 3422 | SEO \\| Rule Twitter | P3 | active | zhouhaiyin | 不稳定 |" in result.stdout
```

Add a JSON regression assertion proving `--json` still emits `data.items`.

- [ ] **Step 2: Run the CLI tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/e2e/cli/test_cli.py -k "markdown_table or unstable_row" -q`

Expected: FAIL because non-JSON output currently prints a Python object representation.

- [ ] **Step 3: Implement the focused renderer**

```python
from zentao_ai.zentao.models import BugPage


def _cell(value: object) -> str:
    text = "unknown" if value is None or str(value).strip() == "" else str(value)
    return " ".join(text.splitlines()).replace("|", r"\|")


def render_bug_table(page: BugPage) -> str:
    lines = [
        "| Bug号 | 标题 | 优先级 | 状态 | 负责人 | 快照稳定性 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for bug in page.items:
        stable = "稳定" if bug.snapshot_stable else "不稳定"
        cells = (bug.id, bug.title, bug.priority, bug.status, bug.assignee, stable)
        lines.append("| " + " | ".join(_cell(value) for value in cells) + " |")
    if not page.items:
        lines.append("| - | 无 | - | - | - | - |")
    return "\n".join(lines)
```

In `bugs user` and `bugs mine`, keep `_emit(page, True)` for JSON and use `typer.echo(render_bug_table(page))` otherwise.

- [ ] **Step 4: Run CLI tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/e2e/cli/test_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/zentao_ai/cli/bug_table.py src/zentao_ai/cli/bug_commands.py tests/e2e/cli/test_cli.py
git commit -m "feat: render bug queries as markdown tables"
```

### Task 5: Gate Unstable Comments and Repairs With Exact Authorization

**Files:**
- Modify: `src/zentao_ai/safety/actions.py`
- Modify: `src/zentao_ai/safety/authorization.py`
- Create: `src/zentao_ai/workflows/snapshot_guard.py`
- Modify: `src/zentao_ai/workflows/comments.py`
- Modify: `src/zentao_ai/workflows/repair.py`
- Test: `tests/unit/safety/test_authorization.py`
- Test: `tests/unit/workflows/test_comment_safety_matrix.py`
- Test: `tests/unit/workflows/test_repair_matrix.py`

**Interfaces:**
- Consumes: `AuthorizationContext.snapshotStable`, exact `AuthorizationRecord`, and before/after `BugSnapshot` values.
- Produces: `unstable_snapshot_matches(before: BugSnapshot, after: BugSnapshot) -> bool`.
- Rule: stable snapshots follow existing gates; unstable comments and `write_code` additionally require the exact current-turn record and a matching fresh snapshot.

- [ ] **Step 1: Write failing authorization tests**

```python
def test_unstable_comment_requires_exact_current_turn_record():
    action = ActionRequest(action="comment", bugId="3422", parameters={"body": "x"})
    common = dict(commentEnabled=True, snapshotStable=False, historyChecked=True,
                  cooldownPassed=True, idempotencyPassed=True, currentTurnId="turn-1")
    assert not authorize(action, AuthorizationContext(**common)).allowed
    approved = record("comment", bug="3422", parameters={"body": "x"})
    assert authorize(action, AuthorizationContext(
        **common, authorizationRecords=(approved,)
    )).allowed


def test_unstable_code_write_requires_exact_bug_action_record():
    action = ActionRequest(action="write_code", bugId="3422")
    base = dict(codeWriteEnabled=True, routingUnique=True,
                repositoryGuardPassed=True, snapshotStable=False,
                currentTurnId="turn-1")
    assert not authorize(action, AuthorizationContext(**base)).allowed
    approved = record("write_code", bug="3422")
    assert authorize(action, AuthorizationContext(
        **base, authorizationRecords=(approved,)
    )).allowed
```

- [ ] **Step 2: Run authorization tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/safety/test_authorization.py -q`

Expected: FAIL because comments require `snapshotStable=True` and code writes do not yet distinguish unstable snapshots.

- [ ] **Step 3: Implement conditional exact authorization**

```python
if name == "comment":
    gates = (
        context.commentEnabled,
        context.historyChecked,
        context.cooldownPassed,
        context.idempotencyPassed,
    )
    allowed = all(gates) and exact_record
    reason = "COMMENT_GATES_PASSED" if allowed else "COMMENT_GATES_FAILED"
    return AuthorizationDecision(allowed=allowed, reason=reason)

if name == "write_code":
    code_gates = (
        context.codeWriteEnabled
        and context.routingUnique
        and context.repositoryGuardPassed
    )
    allowed = code_gates and (context.snapshotStable or exact_record)
    reason = "CODE_WRITE_GATES_PASSED" if allowed else "CODE_WRITE_GATES_FAILED"
    return AuthorizationDecision(allowed=allowed, reason=reason)
```

The comment path remains exact-authorized for stable and unstable snapshots, preserving current behavior.

- [ ] **Step 4: Write failing fresh-snapshot guard tests**

```python
def test_unstable_snapshot_guard_compares_available_safety_fields():
    before = BugSnapshot(id=3422, status="active", assignee="zhouhaiyin",
                         version=None, snapshotVersion=None, snapshotStable=False)
    assert unstable_snapshot_matches(before, before.model_copy())
    assert not unstable_snapshot_matches(
        before, before.model_copy(update={"assignee": "other"})
    )
    assert not unstable_snapshot_matches(
        before, before.model_copy(update={"status": "closed"})
    )
```

Add workflow tests proving the provider is re-queried before comment/write and no side-effect adapter is called when the guard returns false.

- [ ] **Step 5: Run workflow tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/workflows/test_comment_safety_matrix.py tests/unit/workflows/test_repair_matrix.py -k unstable -q`

Expected: FAIL because the guard and pre-side-effect re-query do not exist.

- [ ] **Step 6: Implement the fresh-snapshot guard and wire it before side effects**

```python
from zentao_ai.zentao.models import BugSnapshot


def unstable_snapshot_matches(before: BugSnapshot, after: BugSnapshot) -> bool:
    if str(before.id) != str(after.id):
        return False
    if before.snapshot_stable or after.snapshot_stable:
        return before.snapshot_version == after.snapshot_version
    return (
        before.status == after.status
        and before.assignee == after.assignee
        and before.title == after.title
        and before.priority == after.priority
    )
```

Immediately before comment POST or patch execution, call `query_bug_detail(bug_id, allow_unstable=True)`, run this guard, and fail closed with `UNSTABLE_SNAPSHOT_CHANGED` when it returns false. The exact authorization is consumed only for that attempted action.

- [ ] **Step 7: Run safety and workflow tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/safety/test_authorization.py tests/unit/workflows/test_comment_safety_matrix.py tests/unit/workflows/test_repair_matrix.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add src/zentao_ai/safety/actions.py src/zentao_ai/safety/authorization.py src/zentao_ai/workflows/snapshot_guard.py src/zentao_ai/workflows/comments.py src/zentao_ai/workflows/repair.py tests/unit/safety/test_authorization.py tests/unit/workflows/test_comment_safety_matrix.py tests/unit/workflows/test_repair_matrix.py
git commit -m "feat: authorize unstable bug actions exactly"
```

### Task 6: Full Regression and Contract Documentation

**Files:**
- Modify: `plugins/zentao-ai-bug/skills/zentao-ai-bug/SKILL.md`
- Modify: `plugins/zentao-ai-bug/skills/zentao-ai-bug/personal-bug-agent.md`
- Test: `tests/contract/test_plugin_package.py`
- Test: `tests/test_zentao_skill_contract.py`

**Interfaces:**
- Documents: degraded query fields, Markdown table columns, and exact unstable-snapshot authorization.
- Preserves: team reports remain read-only and permanent deletion remains forbidden.

- [ ] **Step 1: Write failing skill-contract assertions**

```python
def test_skill_documents_unstable_snapshot_query_and_exact_action_gate():
    text = skill_text("zentao-ai-bug")
    for phrase in (
        "snapshotStable=false",
        "Bug号 | 标题 | 优先级 | 状态",
        "当前轮次",
        "具体 Bug",
        "具体动作",
    ):
        assert phrase in text
```

- [ ] **Step 2: Run contract tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/contract/test_plugin_package.py tests/test_zentao_skill_contract.py -q`

Expected: FAIL because the installed contract does not describe degraded snapshots or table output.

- [ ] **Step 3: Update the skill contract**

Add a concise section stating:

```markdown
缺少稳定版本的只读 Bug 仍保留在查询结果中，字段包括 Bug 号、标题、优先级、状态、负责人，且固定标记 `snapshotVersion=null`、`snapshotStable=false`。CLI 默认使用 Markdown 表格展示。此类 Bug 的评论或本地代码修复必须取得当前轮次针对具体 Bug 和具体动作的精确人工确认，并在副作用前重新查询；其余历史、冷却、幂等、仓库和测试门禁不得绕过。
```

- [ ] **Step 4: Run the full verification suite**

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests pass with zero failures.

Run: `.venv\Scripts\python.exe -m ruff check src tests`

Expected: exit 0 with no diagnostics.

Run: `.venv\Scripts\python.exe -m mypy src`

Expected: exit 0 with no errors.

- [ ] **Step 5: Perform an installed CLI smoke test**

Run: `.venv\Scripts\zentao-ai.exe bugs user 周海音 --scope-mode session-visible --status unclosed --project F:\每日工作`

Expected: Markdown table with the six designed columns; any versionless rows remain visible and show `不稳定`.

- [ ] **Step 6: Commit**

```powershell
git add plugins/zentao-ai-bug/skills/zentao-ai-bug/SKILL.md plugins/zentao-ai-bug/skills/zentao-ai-bug/personal-bug-agent.md tests/contract/test_plugin_package.py tests/test_zentao_skill_contract.py
git commit -m "docs: define unstable bug query contract"
```
