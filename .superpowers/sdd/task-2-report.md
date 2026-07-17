# Task 2 Report

## RED evidence

- Provider/model run: 8 failures. `ZentaoEndpoints.login` was absent, password auth sent Basic directly, and invalid login envelopes did not raise.
- Runtime run: fallback test failed with uncaught `CredentialUnavailableError` for the unavailable API token.

## GREEN evidence

- Focused provider and runtime suite: 35 passed.
- Password login accepts top-level and nested token envelopes, caches the token on the provider instance, and uses it as a subsequent bearer credential.
- Invalid token envelopes raise exactly `login: missing token` without rendering password or raw payload markers.

## Files

- `src/zentao_ai/zentao/http_provider.py`
- `src/zentao_ai/zentao/models.py`
- `src/zentao_ai/cli/runtime.py`
- `tests/integration/zentao/test_http_provider.py`
- `tests/unit/cli/test_runtime.py`

## Verification

- `python -m ruff check src/zentao_ai/zentao/http_provider.py src/zentao_ai/zentao/models.py src/zentao_ai/cli/runtime.py tests/integration/zentao/test_http_provider.py tests/unit/cli/test_runtime.py`: `All checks passed!`
- `python -m ruff format --check src/zentao_ai/zentao/http_provider.py src/zentao_ai/zentao/models.py src/zentao_ai/cli/runtime.py tests/integration/zentao/test_http_provider.py tests/unit/cli/test_runtime.py`: `5 files already formatted`.
- Mypy for three changed source files: success.
- `git diff --check`: success.
- Implementation commit: `ec9098add54709770f331ea40ced97a6162048f8` (`fix: support password token login`).

## Self-review

- API-token precedence remains unchanged.
- Runtime catches only `CredentialUnavailableError`; credential backend failures propagate.
- Acquired tokens are held only in `_password_token` and are never persisted or represented.
- GET retry bounds and retry decision logic are unchanged.

## Concerns

- Reauthentication after an expired cached password token is intentionally deferred to Task 3.

## Transport sanitization review fix

- RED: `python -m pytest -q tests/integration/zentao/test_http_provider.py -k "password_login_transport_error"` failed because the raw `httpx.ConnectError` escaped with the synthetic password/raw marker.
- GREEN: `python -m pytest -q tests/integration/zentao/test_http_provider.py` completed with `34 passed in 0.46s`.
- `python -m ruff check src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py`: `All checks passed!`
- `python -m ruff format --check src/zentao_ai/zentao/http_provider.py tests/integration/zentao/test_http_provider.py`: `2 files already formatted`.
- Fix commit: `ecc8ef9134d14e72ba5f9b1ba00b4d0923bd6079` (`fix: sanitize password login transport errors`).
- The login transport boundary now converts `httpx.TransportError` to exact sanitized `TransportError("login: transport failure")` from `None`, with one attempt and no retry.
