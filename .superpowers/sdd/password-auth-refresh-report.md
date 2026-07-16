# Password authentication refresh

Implemented password fallback when no API token is available. `HttpZentaoProvider`
logs in against `/api.php/v2/users/login` on first request, caches the returned
token in memory, and retries once after an authentication response. API tokens
remain highest precedence. Passwords are never persisted by runtime or emitted
in logs/results.

The integration regression test covers login request shape and token caching.
