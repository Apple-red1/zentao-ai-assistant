# Zentao API v2 Read Adapter Design

## Goal

Replace the unavailable synthetic read routes used by the standalone CLI with official Zentao API v2 product and Bug routes, while preserving the assistant's existing scoped, read-only, fail-closed contracts.

## Confirmed Context

Password login succeeds and returns a usable in-memory token. Real read requests then fail before JSON normalization because `/api/bugs/statistics` and `/api/bugs/mine` return HTTP 404 HTML.

The supported official API v2 routes are:

- `GET /api.php/v2/products`
- `GET /api.php/v2/products/{productID}/bugs`
- `GET /api.php/v2/bugs/{bugID}`

## Read Flow

### Product resolution

The provider requests the product catalog with `browseType=all`, bounded `recPerPage`, and explicit `pageID`. It accepts only a successful JSON object containing a `products` array. Each product must have a non-blank `id` and `name` to participate in routing.

Configured `scopeNames` are matched to product names using exact normalized text comparison. Unknown or ambiguous names are not guessed. Their absence is reflected in incomplete coverage rather than silently treated as an empty successful result.

### My Bug query

For each uniquely resolved product ID, the provider requests:

`GET /api.php/v2/products/{productID}/bugs?browseType=assignedtome`

The provider sends explicit pagination values and respects the existing page/page-size contract. Results from all scoped products are combined deterministically and deduplicated by Bug ID. Query count remains bounded by the configured scopes and requested page.

### Bug normalization

Official v2 Bug objects are normalized to the existing `BugSnapshot` model:

- `id`, `status`, title, steps, creator/openedBy, and assignee/assignedTo use their official fields.
- `lastEditedDate` is the preferred stable snapshot version.
- If `lastEditedDate` is absent, a non-blank official `version` may be used.
- If neither stable value exists, normalization raises a sanitized `ContractError`; it never invents a version from the current time or content hash.

### Statistics

`bug_statistics()` will no longer call a nonexistent statistics route. It will perform the smallest official read needed to prove connection and permission and derive aggregate counts only from a complete bounded result. Unknown or truncated data is represented as incomplete rather than exact statistics.

For doctor, a successful product-catalog request is sufficient for the connection check. The query-permission check remains a one-item scoped `query_my_bugs` call.

## Error Handling and Security

- 401/407, 403, transport errors, 5xx responses, non-JSON bodies, malformed envelopes, unresolved scopes, and missing stable versions retain sanitized fail-closed behavior.
- Only official read routes are used by doctor and verification.
- No Bug state, comments, steps, credentials, configuration, or repository content is modified.
- Passwords and tokens remain memory-only and never appear in errors, reports, or raw diagnostics.

## Compatibility

The existing provider interface remains unchanged. Endpoint models gain official product-list and product-Bug-list templates. Synthetic endpoint assumptions are removed from production runtime but focused MockTransport tests may continue to inject custom endpoint values.

Write endpoints are out of scope for this adapter and remain unchanged.

## Testing

- Product catalog success, pagination, malformed envelopes, duplicate/unknown names, and sanitized failures.
- Scoped product-name-to-ID resolution with deterministic ordering.
- Assigned-to-me query parameters and bounded pagination.
- Cross-product deduplication by Bug ID.
- Official Bug field normalization and `lastEditedDate` snapshot version.
- Missing stable version failure.
- Statistics/doctor connection no longer calls `/api/bugs/statistics`.
- Existing password login, reauthentication, API-token precedence, write safety, and secret-redaction tests remain green.
- Final real `zentao-ai doctor --project F:\每日工作 --json` passes all required checks.

## Acceptance Criteria

- Real doctor no longer receives 404 from synthetic read routes.
- `credentials`, `connection`, and `query-permission` pass with the stored password and configured scoped products.
- All read results obey configured scope and deterministic coverage rules.
- No secrets are persisted or rendered.
- Full pytest, Ruff check, mypy, and targeted formatting checks pass.
