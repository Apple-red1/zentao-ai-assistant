# Zentao API v2 Read Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace synthetic 404 read routes with official Zentao API v2 product and scoped Bug reads while retaining the provider's safe public interface.

**Architecture:** Add official product-catalog and product-Bug endpoint templates, then resolve configured product names to IDs and aggregate `assignedtome` Bug pages. Normalize official Bug fields into existing immutable models and use catalog access for the doctor connection check.

**Tech Stack:** Python, HTTPX, Pydantic, Typer, pytest, Ruff, mypy.

## Global Constraints

- API token precedence and password-derived in-memory token behavior remain unchanged.
- Doctor and verification use read-only official routes only.
- Unknown or ambiguous scope names are never guessed.
- Stable snapshot version is `lastEditedDate`, falling back only to non-blank official `version`.
- Missing stable version, malformed envelopes, authentication, permission, and transport failures remain sanitized and fail closed.
- No Bug writes, configuration mutation, credential persistence, or raw response logging.

---

### Task 1: Official Product Catalog Contract

**Files:**
- Modify: `src/zentao_ai/zentao/models.py`
- Modify: `src/zentao_ai/zentao/http_provider.py`
- Modify: `src/zentao_ai/cli/runtime.py`
- Test: `tests/integration/zentao/test_http_provider.py`
- Test: `tests/unit/cli/test_runtime.py`

**Interfaces:**
- Produces endpoint defaults `products=/api.php/v2/products` and `productBugs=/api.php/v2/products/{product_id}/bugs`.
- Produces a private catalog loader returning validated product ID/name pairs and safe pagination metadata.

Expected endpoint model additions:

```python
products: str = "/api.php/v2/products"
product_bugs: str = Field(
    "/api.php/v2/products/{product_id}/bugs", alias="productBugs"
)
```

- [ ] Add failing tests asserting production runtime official paths and provider catalog request parameters `browseType=all`, `recPerPage`, `pageID`.
- [ ] Add malformed/non-JSON/status-failure catalog tests with sanitized errors.
- [ ] Run focused tests and record RED caused by missing endpoints/catalog support.
- [ ] Add endpoint fields and the smallest validated catalog loader. Accept only object envelopes with a `products` list; ignore malformed individual products but fail when the envelope itself is invalid.
- [ ] Preserve injectable endpoint values for MockTransport tests.
- [ ] Run focused tests, Ruff, mypy, and diff check.
- [ ] Commit: `feat: add official Zentao product catalog`.

### Task 2: Scoped Assigned-to-Me Bug Aggregation

**Files:**
- Modify: `src/zentao_ai/zentao/http_provider.py`
- Modify: `tests/integration/zentao/test_http_provider.py`

**Interfaces:**
- Consumes validated product ID/name pairs.
- Produces existing `query_my_bugs(scope_names, page, page_size) -> BugPage` using official product Bug routes.
- Preserves `BugSnapshot` and `Coverage` public models.

Expected normalization rule:

```python
stable_version = payload.get("lastEditedDate") or payload.get("version")
if not isinstance(stable_version, (str, int)) or not str(stable_version).strip():
    raise ContractError("query_my_bugs: missing stable version")
```

Expected official query parameters:

```python
params={
    "browseType": "assignedtome",
    "recPerPage": page_size,
    "pageID": page,
}
```

- [ ] Add failing tests for exact normalized scope-name matching, unknown/ambiguous names, deterministic product order, and official `browseType=assignedtome`, `recPerPage`, `pageID` parameters.
- [ ] Add failing aggregation tests for cross-product Bug-ID dedupe and coverage/truncation semantics.
- [ ] Add official Bug normalization tests mapping `openedBy`, `assignedTo`, `title`, `steps`, `status`, and `lastEditedDate`.
- [ ] Add missing stable-version test expecting a sanitized `ContractError`.
- [ ] Run focused tests and record RED.
- [ ] Implement catalog resolution, bounded per-product reads, deterministic merge/dedupe, and stable-version normalization without changing the public method signature.
- [ ] Ensure raw values are never placed in error messages.
- [ ] Run the full provider test file, Ruff, mypy, and diff check.
- [ ] Commit: `feat: query scoped Bugs through Zentao v2`.

### Task 3: Statistics Connection Check and Real Verification

**Files:**
- Modify: `src/zentao_ai/zentao/http_provider.py`
- Modify: `tests/integration/zentao/test_http_provider.py`
- Verify: `tests/e2e/cli/test_cli.py`

**Interfaces:**
- Preserves `bug_statistics() -> dict[str, int]`.
- Uses the official catalog as a read-only connection/permission proof instead of `/api/bugs/statistics`.

- [ ] Add a failing test proving `bug_statistics()` calls the official product catalog and never the synthetic statistics route.
- [ ] Implement the minimal catalog-derived statistics result without claiming exact Bug counts from incomplete data.
- [ ] Run provider/doctor focused tests and record GREEN.
- [ ] Run full pytest, Ruff check for changed files, Ruff format check for changed files, mypy, and `git diff --check`.
- [ ] Confirm editable install provenance points to this worktree.
- [ ] Run real read-only `zentao-ai doctor --project F:\每日工作 --json` and record only sanitized check results.
- [ ] If real official envelopes differ, stop with safe key/type evidence and add a focused test before normalization changes.
- [ ] Commit an adapter correction only after a new focused failing test reproduces the safe observed structure; rerun verification until all required doctor checks pass or a non-code permission/scope blocker is proven.
