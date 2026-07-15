# Zentao Inline Image Upload Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `updateBugStepsWithImage` so it follows Zentao's editor-image upload protocol and inserts the returned image into Bug steps without changing any other MCP behavior.

**Architecture:** Keep the public MCP tool and schema unchanged. Add private, side-effect-free HTML/form/upload-response helpers in `zentao-api.js`, then change only `updateBugStepsWithImage` to perform edit-page discovery, one image upload, one Bug edit submission, and post-write verification. Existing `webRequest` behavior remains the default; a scoped option exposes a sanitized error-body summary only for this image path.

**Tech Stack:** Node.js ESM, built-in `fetch`/`FormData`/`Blob`, `node:test`, `node:assert`.

## Global Constraints

- Modify only `src/services/zentao-api.js` and `tests/zentao-api.test.js`.
- Do not change MCP tool names, schemas, permissions, configuration, or non-image operations.
- Continue to accept only PNG/JPEG/WebP regular files up to 10 MiB.
- Accept only same-origin upload endpoints and same-origin or site-relative returned image URLs.
- Do not retry a write after an unknown result.
- Never expose Cookie, password, token, authorization header, full HTML, or local sensitive paths in errors.

---

### Task 1: Reproduce the Real Two-Stage Editor Protocol

**Files:**
- Modify: `C:\Users\wwtlove66\Documents\Codex\2026-07-10\https-xm-wixcn-com-index-php\zentao-mcp-server\tests\zentao-api.test.js`
- Modify: `C:\Users\wwtlove66\Documents\Codex\2026-07-10\https-xm-wixcn-com-index-php\zentao-mcp-server\src\services\zentao-api.js:214`

**Interfaces:**
- Consumes: `ZentaoApi.updateBugStepsWithImage(bugId, {steps, imagePath, imageAlt})`.
- Produces: the same return object `{before, mutation, after, image}`; no public API change.

- [ ] **Step 1: Replace the false-positive image test with a failing protocol test**

Create an edit-page fixture containing a form action, hidden UID, textarea, select, checked and unchecked controls, duplicate names, and an editor upload URL. Make `fetchImpl` return that page, a successful upload response containing `/data/upload/1/figure.png`, a successful edit response, and before/after snapshots. Assert call order is GET edit page → POST upload endpoint → POST edit action; assert the edit `steps` contains escaped `<img src="/data/upload/1/figure.png" alt="图1">`, and assert no `files[]` is sent to the edit action.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
& 'C:\nvm4w\nodejs\node.exe' --test --test-name-pattern 'two-stage editor image protocol' tests/zentao-api.test.js
```

Expected: FAIL because the existing implementation sends `files[]` directly to the Bug edit endpoint and never calls the editor upload endpoint.

- [ ] **Step 3: Implement minimal endpoint and response parsing helpers**

Add private helpers in `zentao-api.js`:

```js
function extractFormAction(html, fallbackPath) { /* safe same-page action extraction */ }
function extractEditorUploadPath(html) { /* data attribute or quoted script URL */ }
function parseUploadedImagePath(text) { /* structured JSON first, then bounded known response shapes */ }
function assertSameOriginWebPath(webRoot, candidate, label) { /* returns a site-relative or same-origin URL */ }
function escapeHtmlAttribute(value) { /* &, <, >, quote escaping */ }
```

Update only `updateBugStepsWithImage` to upload the validated Blob first, append a `<p><img ...></p>` fragment to `steps`, and submit the edit form without `files[]` or `imageAlt` pseudo-fields.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the same focused command. Expected: PASS with exactly one upload POST and one edit POST.

---

### Task 2: Preserve Complete Successful Form Controls

**Files:**
- Modify: `C:\Users\wwtlove66\Documents\Codex\2026-07-10\https-xm-wixcn-com-index-php\zentao-mcp-server\tests\zentao-api.test.js`
- Modify: `C:\Users\wwtlove66\Documents\Codex\2026-07-10\https-xm-wixcn-com-index-php\zentao-mcp-server\src\services\zentao-api.js:573`

**Interfaces:**
- Produces private `extractSuccessfulFormControls(html): Array<[string, string]>`.
- `updateBugStepsWithImage` consumes the returned ordered pairs and appends them to `FormData`.

- [ ] **Step 1: Write failing serialization assertions**

In the protocol test, assert that the edit POST retains hidden/text values, textarea values, selected options, checked checkbox/radio values, and both duplicate-name values. Assert that disabled controls, unchecked checkbox/radio, button/submit/reset, and original file inputs are absent.

- [ ] **Step 2: Run the focused test and verify RED**

Expected: FAIL because `extractFormInputs` reads only inputs, ignores successful-control state, and collapses duplicate names.

- [ ] **Step 3: Implement the scoped successful-control serializer**

Add `extractSuccessfulFormControls` without modifying or replacing `extractFormInputs`. Preserve ordered duplicate values and append them with `FormData.append`; replace only the `steps` entries with the newly composed HTML.

- [ ] **Step 4: Run the focused test and verify GREEN**

Expected: PASS with all successful controls preserved and excluded controls absent.

---

### Task 3: Fail Closed and Improve Scoped Diagnostics

**Files:**
- Modify: `C:\Users\wwtlove66\Documents\Codex\2026-07-10\https-xm-wixcn-com-index-php\zentao-mcp-server\tests\zentao-api.test.js`
- Modify: `C:\Users\wwtlove66\Documents\Codex\2026-07-10\https-xm-wixcn-com-index-php\zentao-mcp-server\src\services\zentao-api.js:345`

**Interfaces:**
- Adds optional private request option `includeSanitizedErrorSummary: true`.
- Default `webRequest` behavior for every existing caller remains unchanged.

- [ ] **Step 1: Add failing security and failure-order tests**

Add tests that reject a cross-origin upload endpoint, reject a cross-origin returned image URL, do not call the Bug edit endpoint when upload fails, and include a bounded sanitized response summary for an image-path HTTP 500 while removing cookie/token/password-like values.

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
& 'C:\nvm4w\nodejs\node.exe' --test --test-name-pattern 'image upload|same-origin|sanitized' tests/zentao-api.test.js
```

Expected: FAIL because origin validation and scoped response summaries do not exist.

- [ ] **Step 3: Implement minimal fail-closed validation and diagnostics**

Validate upload action and returned image URL before each write boundary. When `includeSanitizedErrorSummary` is true, normalize response text to one line, redact credential-shaped fields, strip tags, and cap the summary at 300 characters before attaching it to the existing HTTP error message. Do not change default callers.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Expected: all new image tests pass and no edit POST occurs after an upload-stage failure.

---

### Task 4: Regression Verification

**Files:**
- Test only: `C:\Users\wwtlove66\Documents\Codex\2026-07-10\https-xm-wixcn-com-index-php\zentao-mcp-server\tests\zentao-api.test.js`
- Test only: `C:\Users\wwtlove66\Documents\Codex\2026-07-10\https-xm-wixcn-com-index-php\zentao-mcp-server\tests\server.test.js`

**Interfaces:**
- Verifies all existing public interfaces remain unchanged.

- [ ] **Step 1: Run the service tests**

```powershell
& 'C:\nvm4w\nodejs\node.exe' --test tests/zentao-api.test.js
```

Expected: PASS.

- [ ] **Step 2: Run the complete MCP suite**

```powershell
& 'C:\nvm4w\nodejs\npm.cmd' test
```

Expected: all tests pass with no new warnings or unhandled rejections.

- [ ] **Step 3: Inspect the final diff**

Confirm changes are limited to the two approved files, `updateBugStepsWithImage` and new private helpers; verify `updateBugSteps`, `addBugComment`, tool registration, schemas, configuration, and permission guards are unchanged.

- [ ] **Step 4: Do not perform a live Bug write automatically**

Report the verified code fix. A live retry requires a new current-turn authorization containing Bug ID, complete steps, image path, image label, and `confirm:true` semantics.

## Plan Self-Review

- Spec coverage: two-stage upload, form preservation, same-origin validation, diagnostics, no retries, regression verification, and live-write authorization are covered.
- Placeholder scan: no deferred implementation items remain.
- Type consistency: helper outputs and `updateBugStepsWithImage` inputs/outputs are consistent across all tasks.
