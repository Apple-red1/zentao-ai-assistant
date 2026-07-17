# Password-Based Token Login Design

## Goal

Allow `zentao-ai` to operate when the user has stored a Zentao account password but has not separately stored an API token. The CLI will authenticate with the configured account and stored password, extract the token returned by the login endpoint, and use that token for subsequent requests.

## Scope

- Treat either a stored API token or a stored password as a valid credential in `zentao-ai doctor`.
- Preserve API-token precedence when both credentials exist.
- For password authentication, call the configured login endpoint and extract a non-blank token from the supported Zentao response envelope.
- Cache the acquired token only in the current provider process.
- On an authenticated request receiving HTTP 401 or 407, discard the cached password-derived token, log in once more, and retry the request once.
- Keep all error messages sanitized. Never include the account password, acquired token, cookie, or raw authentication response.

## Non-Goals

- Do not persist the acquired token to YAML, SQLite, logs, reports, or Windows Credential Manager.
- Do not change Bug data, comments, state, assignee, or repository content as part of authentication.
- Do not add unbounded authentication retries.
- Do not weaken API-token authentication or change its precedence.

## Design

### Credential readiness

The doctor credential check will pass when the runtime credential store contains either a non-blank `api-token` or a non-blank `password`. The connection and query-permission checks remain authoritative: a present but invalid credential will still fail those checks.

### Login and token extraction

When password mode is selected, the provider sends the configured account and password to the configured login endpoint over the existing HTTP client. The response is decoded using the existing sanitized HTTP error mapping.

Token extraction will support the response shapes explicitly covered by tests and observed in the supported Zentao API contract. Extraction must be narrow: it will accept only named token fields at documented envelope locations, require a string value, trim only for validation, and reject missing, blank, or incorrectly typed values with `ContractError("login: missing token")`.

### Token lifetime and retry

The password-derived token is held only on the provider instance. Subsequent requests send it using the same bearer-token path as an explicitly supplied API token. If a request returns 401 or 407, the provider clears the cached token, performs one fresh login, rebuilds the authorization header, and retries the original request once. A second authentication failure is returned without another retry.

### Security behavior

API tokens remain preferred over passwords. Passwords are used only in the login request; password-derived tokens are never serialized or logged. Exceptions expose only operation names, sanitized status codes, optional request IDs, and stable contract-error labels.

## Testing

Tests will be written before production changes and must demonstrate failure on the current implementation.

- Doctor passes credential readiness with API token only.
- Doctor passes credential readiness with password only.
- Doctor fails credential readiness when both are absent.
- Password login extracts a token from each supported response envelope and uses it as a bearer token.
- Missing, blank, and non-string token values fail with the sanitized contract error.
- A 401/407 causes exactly one re-login and one request retry.
- A second authentication failure does not loop.
- API-token precedence remains unchanged.
- Secret values do not appear in provider representations, CLI JSON, or exception messages.

After unit and integration tests pass, the local CLI will be reinstalled from the modified source and `zentao-ai doctor` will be run from the project directory. Doctor is read-only with respect to Zentao Bug data.

## Acceptance Criteria

- A user with a configured account and valid stored password can run `zentao-ai doctor` without separately entering an API token.
- `credentials`, `connection`, and `query-permission` pass when the server returns a supported login response and the account has query permission.
- No acquired token is persisted.
- Existing API-token users retain current behavior.
- The full relevant test suite passes.
