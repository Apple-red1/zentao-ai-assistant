# Windows UTF-8 JSON stdout fix

## Root cause

Both repository guard entrypoints serialize JSON with `ensure_ascii=False` and
then use `print`. On Windows, a redirected `sys.stdout` can retain the system
code page, so valid Unicode JSON is emitted as non-UTF-8 bytes. A parent process
that consumes the CLI contract as UTF-8 then raises `UnicodeDecodeError`.

Affected entrypoints:

- `scripts/direct-branch-guard.py`
- `python -m zentao_ai.repository.cli`

## TDD evidence

The regression runs both real subprocess entrypoints with cp1252 stdio, captures
raw bytes, and strictly decodes stdout as UTF-8.

RED, before the production change:

```text
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 46
1 failed
```

GREEN, after the production change:

```text
tests/contract/test_direct_branch_guard_compatibility.py::test_guard_entrypoints_write_utf8_json_with_non_utf8_stdio
1 passed in 3.25s
```

## Fix

Immediately before emitting JSON, each output function reconfigures a real
`io.TextIOWrapper` stdout to UTF-8. The type guard preserves compatibility with
captured or embedded text streams that do not expose `reconfigure`.

No parent-process decoder or ambient environment setting was changed to mask the
problem.

## Verification

Using bundled Python 3.12.13 on Windows:

```text
python -X utf8 -m pytest
456 passed, 2 skipped in 50.18s

python -X utf8 -m ruff check .
All checks passed!

python -X utf8 -m mypy
Success: no issues found in 56 source files
```

## Concerns

None known. The regression deliberately uses a single-byte Windows-compatible
encoding to make the failure deterministic; the production contract remains
UTF-8 regardless of the inherited redirected stdout encoding.
