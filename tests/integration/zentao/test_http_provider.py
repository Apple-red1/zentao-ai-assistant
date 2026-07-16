from __future__ import annotations

import hashlib
import json
from types import MappingProxyType

import httpx
import pytest
from pydantic import SecretStr

from zentao_ai.zentao import (
    AuthenticationError,
    ContractError,
    HttpZentaoProvider,
    PermissionDeniedError,
    UnknownWriteResultError,
    ZentaoAuth,
    ZentaoEndpoints,
)


def provider(handler: httpx.MockTransport, **kwargs: object) -> HttpZentaoProvider:
    return HttpZentaoProvider(
        base_url="https://zentao.invalid",
        endpoints=ZentaoEndpoints(),
        transport=handler,
        **kwargs,
    )


def test_query_normalizes_version_and_pagination() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.params["page"] == "2"
        return httpx.Response(
            200,
            json={
                "items": [{"id": 7, "status": "open", "version": 3}],
                "page": 2,
                "pageSize": 20,
                "total": 21,
            },
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(page=2)
    assert result.items[0].snapshot_version == "3"
    assert result.coverage.total == 21


def test_missing_version_is_contract_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"id": 7, "status": "open"})
    )
    with pytest.raises(ContractError, match="query_bug_detail"):
        provider(transport).query_bug_detail(7)


def test_auth_secrets_are_only_sent_in_required_fields() -> None:
    seen: list[httpx.Request] = []
    observations: list[tuple[bool, bool]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        observations.append(
            (
                request.headers.get("Authorization", "").startswith("Bearer "),
                "Cookie" in request.headers,
            )
        )
        return httpx.Response(200, json={"items": []})

    auth = ZentaoAuth(
        api_token=SecretStr("token-secret"), web_cookie=SecretStr("cookie-secret")
    )
    instance = provider(httpx.MockTransport(handle), auth=auth)
    assert "token-secret" not in repr(instance)
    instance.query_my_bugs()
    assert observations == [(True, False)]


def test_cookie_is_used_when_it_is_the_only_auth_mode() -> None:
    observations: list[tuple[bool, bool]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        observations.append(
            ("Cookie" in request.headers, "Authorization" in request.headers)
        )
        return httpx.Response(200, json={"items": []})

    provider(
        httpx.MockTransport(handle),
        auth=ZentaoAuth(web_cookie=SecretStr("synthetic-cookie")),
    ).query_my_bugs()
    assert observations == [(True, False)]


def test_password_auth_is_request_body_only() -> None:
    observed = False

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal observed
        body = json.loads(request.content)
        observed = (
            body.get("account") == "alice"
            and isinstance(body.get("password"), str)
            and bool(body["password"])
        )
        return httpx.Response(
            200, json={"created": True, "alreadyExists": False, "commentId": "9"}
        )

    auth = ZentaoAuth(username="alice", password=SecretStr("password-secret"))
    provider(httpx.MockTransport(handle), auth=auth).add_bug_comment(
        1, "hello", True, "stable-key"
    )
    assert observed


def test_write_timeout_is_unknown_and_is_not_retried() -> None:
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("secret-value", request=request)

    with pytest.raises(UnknownWriteResultError) as caught:
        provider(httpx.MockTransport(handle)).add_bug_comment(
            1, "hello", True, "stable-key"
        )
    assert calls == 1
    assert "secret-value" not in str(caught.value)


def test_reconcile_requires_exact_structured_match() -> None:
    text = "hello"
    digest = hashlib.sha256(text.encode()).hexdigest()
    history = {
        "items": [
            {
                "id": "c1",
                "idempotencyKey": "key-1",
                "contentHash": digest,
                "created": True,
            }
        ]
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=history))
    result = provider(transport).reconcile_comment("key-1", 1, comment=text)
    assert result.status == "CREATED"


def test_protocol_has_no_destructive_methods() -> None:
    instance = provider(
        httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    )
    assert not hasattr(instance, "delete")
    assert not hasattr(instance, "remove")


@pytest.mark.parametrize(
    "status,error",
    [(401, AuthenticationError), (403, PermissionDeniedError), (422, ContractError)],
)
def test_http_errors_are_classified_without_response_secrets(
    status: int, error: type[Exception]
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status, text="server-secret", headers={"X-Request-Id": "req-7"}
        )
    )
    with pytest.raises(error) as caught:
        provider(transport).query_my_bugs()
    assert "server-secret" not in str(caught.value)
    assert "req-7" in str(caught.value)


def test_get_retries_transient_status_only() -> None:
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"items": []})

    provider(httpx.MockTransport(handle), retry_after_cap=0).query_my_bugs()
    assert calls == 2


def test_comment_already_exists_is_structured() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"created": False, "alreadyExists": True, "commentId": "c2"}
        )
    )
    result = provider(transport).add_bug_comment(2, "note", True, "key-2")
    assert result.status == "ALREADY_EXISTS"


def test_image_update_uses_bytes_and_safe_filename() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert b"picture.png" in request.content
        assert b"PNGDATA" in request.content
        assert b"C:\\private" not in request.content
        return httpx.Response(200, json={"updated": True, "bugId": 1, "version": "4"})

    result = provider(httpx.MockTransport(handle)).update_bug_steps_with_image(
        1, "full steps", b"PNGDATA", "picture.png", "image/png"
    )
    assert result.updated
    with pytest.raises(ValueError):
        provider(httpx.MockTransport(handle)).update_bug_steps_with_image(
            1, "steps", b"x", "C:\\private\\x.png", "image/png"
        )


def test_raw_is_recursively_sanitized_and_deeply_immutable() -> None:
    payload = {
        "id": 1,
        "status": "open",
        "version": "v1",
        "nested": {
            "API-token": "hidden",
            "safe": [{"web_cookie": "hidden", "name": "ok"}],
        },
    }
    result = provider(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ).query_bug_detail(1)
    assert isinstance(result.raw, MappingProxyType)
    assert "API-token" not in result.raw["nested"]
    assert result.raw["nested"]["safe"][0] == MappingProxyType({"name": "ok"})
    with pytest.raises(TypeError):
        result.raw["new"] = "value"  # type: ignore[index]


def test_paths_percent_encode_external_segments() -> None:
    paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.raw_path.decode())
        return httpx.Response(200, json={"items": []})

    provider(httpx.MockTransport(handle)).query_user_bugs("../a/?#")
    assert paths == ["/api/bugs/user/..%2Fa%2F%3F%23?page=1&pageSize=20"]


def test_reconcile_walks_later_pages_for_exact_match() -> None:
    digest = hashlib.sha256(b"exact").hexdigest()

    def handle(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        item = (
            {
                "id": "c9",
                "idempotencyKey": "key",
                "contentHash": digest,
                "created": True,
            }
            if page == 2
            else {"id": "other"}
        )
        return httpx.Response(
            200,
            json={"items": [item], "page": page, "pageSize": 1, "total": 2, "pages": 2},
        )

    result = provider(httpx.MockTransport(handle)).reconcile_comment(
        "key", 1, comment="exact"
    )
    assert result.comment_id == "c9"


def test_password_auth_covers_reads_and_multipart_without_secret_assertions() -> None:
    observations: list[tuple[bool, bool]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        observations.append(
            (
                request.headers.get("Authorization", "").startswith("Basic "),
                b"account" in request.content and b"password" in request.content,
            )
        )
        return httpx.Response(
            200,
            json={"items": []}
            if request.method == "GET"
            else {"updated": True, "bugId": 1},
        )

    instance = provider(
        httpx.MockTransport(handle),
        auth=ZentaoAuth(username="alice", password=SecretStr("synthetic-pass")),
    )
    instance.query_my_bugs()
    instance.update_bug_steps_with_image(1, "steps", b"image", "x.png", "image/png")
    assert observations == [(True, False), (False, True)]


def test_user_history_and_statistics_contracts() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/history"):
            return httpx.Response(
                200,
                json={
                    "items": [{"id": "h1", "action": "opened"}],
                    "page": 2,
                    "pageSize": 5,
                    "total": 6,
                },
            )
        if request.url.path.endswith("/statistics"):
            return httpx.Response(
                200, json={"values": {"open": 4, "closed": 2}, "Secret-Key": "discard"}
            )
        return httpx.Response(
            200, json={"items": [{"id": 2, "status": "open", "version": "v2"}]}
        )

    instance = provider(httpx.MockTransport(handle))
    assert instance.query_user_bugs("alice").items[0].snapshot_version == "v2"
    assert instance.query_bug_history(2, page=2, page_size=5).coverage.total == 6
    stats = instance.bug_statistics()
    assert stats.values["open"] == 4 and "Secret-Key" not in stats.raw


def test_get_does_not_retry_non_transient_and_caps_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    sleeps: list[float] = []
    monkeypatch.setattr("zentao_ai.zentao.http_provider.time.sleep", sleeps.append)

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return (
            httpx.Response(503, headers={"Retry-After": "99"})
            if calls == 1
            else httpx.Response(200, json={"items": []})
        )

    provider(httpx.MockTransport(handle), retry_after_cap=0.25).query_my_bugs()
    assert sleeps == [0.25]
    non_transient_calls = 0

    def non_transient(request: httpx.Request) -> httpx.Response:
        nonlocal non_transient_calls
        non_transient_calls += 1
        return httpx.Response(429)

    with pytest.raises(ContractError):
        provider(httpx.MockTransport(non_transient)).query_my_bugs()
    assert non_transient_calls == 1


def test_created_and_invalid_comment_results() -> None:
    created = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"created": True, "alreadyExists": False, "commentId": "c1"}
        )
    )
    assert provider(created).add_bug_comment(1, "note", True, "key").status == "CREATED"
    invalid = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"created": True, "alreadyExists": True}
        )
    )
    with pytest.raises(ContractError):
        provider(invalid).add_bug_comment(1, "note", True, "key")


def test_mixed_auth_uses_only_highest_precedence_mode() -> None:
    observations: list[tuple[bool, bool, bool, bool]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        observations.append(
            (
                request.headers.get("Authorization", "").startswith("Bearer "),
                "Cookie" in request.headers,
                "password" in body,
                "account" in body,
            )
        )
        return httpx.Response(200, json={"created": True, "alreadyExists": False})

    auth = ZentaoAuth(
        username="alice",
        password=SecretStr("unused-pass"),
        api_token=SecretStr("selected-token"),
        web_cookie=SecretStr("unused-cookie"),
    )
    provider(httpx.MockTransport(handle), auth=auth).add_bug_comment(
        1, "note", True, "key"
    )
    assert observations == [(True, False, False, False)]


def test_password_write_uses_body_without_basic_header() -> None:
    observations: list[tuple[bool, bool]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        observations.append(
            ("Authorization" in request.headers, bool(body.get("password")))
        )
        return httpx.Response(200, json={"created": True, "alreadyExists": False})

    auth = ZentaoAuth(username="alice", password=SecretStr("synthetic-pass"))
    provider(httpx.MockTransport(handle), auth=auth).add_bug_comment(
        1, "note", True, "key"
    )
    assert observations == [(False, True)]


def test_get_retries_connection_then_succeeds_and_exhausts() -> None:
    calls = 0

    def recover(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("synthetic detail", request=request)
        return httpx.Response(200, json={"items": []})

    provider(httpx.MockTransport(recover)).query_my_bugs()
    assert calls == 2

    exhausted = 0

    def fail(request: httpx.Request) -> httpx.Response:
        nonlocal exhausted
        exhausted += 1
        raise httpx.ConnectTimeout("synthetic detail", request=request)

    from zentao_ai.zentao import TransportError

    with pytest.raises(TransportError, match="query_my_bugs"):
        provider(httpx.MockTransport(fail), max_get_retries=2).query_my_bugs()
    assert exhausted == 3


def test_password_auth_logs_in_once_and_caches_token() -> None:
    calls: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api.php/v2/users/login":
            assert json.loads(request.content) == {"account": "alice", "password": "secret"}
            return httpx.Response(200, json={"token": "issued-token"})
        assert request.headers["Authorization"] == "Bearer issued-token"
        return httpx.Response(200, json={"items": []})

    instance = provider(
        httpx.MockTransport(handle),
        auth=ZentaoAuth(username="alice", password=SecretStr("secret")),
    )
    instance.query_my_bugs()
    instance.query_my_bugs()
    assert calls == ["/api.php/v2/users/login", "/api/bugs/mine", "/api/bugs/mine"]


def test_post_remote_protocol_error_is_unknown_without_retry() -> None:
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.RemoteProtocolError("synthetic interruption")

    with pytest.raises(UnknownWriteResultError, match="outcome unknown"):
        provider(httpx.MockTransport(handle)).add_bug_comment(1, "note", True, "key")
    assert calls == 1
