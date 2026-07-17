# Task 3 Report: Bounded Reauthentication and Auth Precedence

## RED

- Command: `python -m pytest tests/integration/zentao/test_http_provider.py -k "reauthenticates_only_once or refreshed_bearer" -vv`
- Result: 2 failed, 34 deselected.
- Expected failures: only one login occurred after repeated 401, and the first 401 raised immediately instead of refreshing the bearer token.

## GREEN

- Focused command: `python -m pytest tests/integration/zentao/test_http_provider.py -k "password or mixed_auth" -q`
- Result: 14 passed, 22 deselected.
- Full provider command: `python -m pytest tests/integration/zentao/test_http_provider.py -q`
- Result: 36 passed.

## Lint and Formatting

- `python -m ruff check src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py`: all checks passed.
- `python -m ruff format --check src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py`: 2 files already formatted.
- `git diff --check`: passed.

## Implementation and Security Review

- Reauthentication is gated on password mode and only the first 401/407.
- The cached password-derived token is cleared, login is performed once, and the original request is retried with a rebuilt bearer header.
- Any caller-provided stale Authorization header is removed during refresh.
- A second 401/407 follows the existing sanitized `AuthenticationError` path without looping.
- Explicit API-token precedence remains unchanged and existing mixed-auth coverage proves password login is not used.
- Login transport failures are not retried by the original-request retry loop.
- Existing GET retry accounting and write outcome safety remain intact.
- Tests assert secrets, acquired tokens, and raw response markers do not appear in the terminal authentication error.

## Commit

- Subject: `fix: bound password token reauthentication`
