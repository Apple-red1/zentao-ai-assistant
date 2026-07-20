# Task 4 report

## Status

Implemented and locally verified. Live read-only verification was blocked fail-closed by the external Zentao contract state.

## Changed files

- `plugins/zentao-ai-bug/skills/zentao-ai-bug/personal-bug-agent.md`
- `tests/contract/test_legacy_feature_inventory.py`
- `.superpowers/sdd/task-4-report.md`

## RED evidence

- Command: `.\.venv\Scripts\python.exe -m pytest -q tests/contract/test_legacy_feature_inventory.py -k assignee_first`
- Result before the documentation correction: 1 failed, 2 deselected.
- Expected failure: `configured-assignee-first` was absent from `personal-bug-agent.md`.

## Verification

- Targeted GREEN: 1 passed, 2 deselected.
- Contract tests: 34 passed, 24 subtests passed.
- `pytest -q`: 542 passed, 2 skipped, 26 subtests passed.
- `ruff check src tests`: all checks passed.
- `mypy src`: success, no issues in 57 source files.
- `git diff --check`: passed with no output.

## Live read-only verification

The commands were passed to the worktree CLI as explicit PowerShell argument arrays. JSON-encoding those arrays before invocation confirmed the CLI received the Unicode values `F:\每日工作`, `AI建站`, and `站点后台` exactly.

Command:

```powershell
.\.venv\Scripts\zentao-ai.exe bugs mine --project 'F:\每日工作' --title-tag AI建站 --status unclosed --json
```

Complete sanitized JSON output (exit code 3):

```json
{"ok": false, "code": 3, "data": null, "error": {"type": "business", "message": "ContractError"}}
```

Command:

```powershell
.\.venv\Scripts\zentao-ai.exe bugs mine --project 'F:\每日工作' --title-tag 站点后台 --status unclosed --json
```

Complete sanitized JSON output (exit code 3):

```json
{"ok": false, "code": 3, "data": null, "error": {"type": "business", "message": "ContractError"}}
```

Command:

```powershell
.\.venv\Scripts\zentao-ai.exe bugs mine --project 'F:\每日工作' --status unclosed --json
```

Complete sanitized JSON output (exit code 3):

```json
{"ok": false, "code": 3, "data": null, "error": {"type": "business", "message": "ContractError"}}
```

Expected IDs `[2537]`, `[3397]`, and `[2537,3397]` therefore could not be verified. No Zentao write command or write tool was invoked.

## Commit hash

- Documentation/tests/report commit: `fab61185e7ede967c96f2e7cbaab106badedb54d`.
- Report-amendment commit: recorded separately in the task handoff because a commit cannot contain its own final object hash.

## Self-review

The contract test directly detects stale assignee-first documentation. The documentation correction is one scoped bullet, retains `mcp__zentao__query_my_bugs`, `status=unclosed`, the existing versioned structured-content envelope, and explicitly prevents product-catalog or pagination incompleteness from erasing candidates. No permission or write behavior changed.

## Concerns

External live verification remains blocked by the sanitized Zentao `ContractError`; local contract and repository gates are green.
