from __future__ import annotations

import hashlib
import json

import httpx
import pytest
from pydantic import SecretStr

from zentao_ai.zentao import (
    AuthenticationError,
    ContractError,
    HttpZentaoProvider,
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

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"items": []})

    auth = ZentaoAuth(
        api_token=SecretStr("token-secret"), web_cookie=SecretStr("cookie-secret")
    )
    instance = provider(httpx.MockTransport(handle), auth=auth)
    assert "token-secret" not in repr(instance)
    instance.query_my_bugs()
    assert seen[0].headers["Authorization"] == "Bearer token-secret"
    assert seen[0].headers["Cookie"] == "cookie-secret"


def test_password_auth_is_request_body_only() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["account"] == "alice" and body["password"] == "password-secret"
        return httpx.Response(
            200, json={"created": True, "alreadyExists": False, "commentId": "9"}
        )

    auth = ZentaoAuth(username="alice", password=SecretStr("password-secret"))
    provider(httpx.MockTransport(handle), auth=auth).add_bug_comment(
        1, "hello", True, "stable-key"
    )


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


@pytest.mark.parametrize("status,error", [(401, AuthenticationError), (403, PermissionError), (422, ContractError)])
def test_http_errors_are_classified_without_response_secrets(status: int, error: type[Exception]) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, text="server-secret", headers={"X-Request-Id": "req-7"}))
    actual_error = error
    if status == 403:
        from zentao_ai.zentao import PermissionDeniedError
        actual_error = PermissionDeniedError
    with pytest.raises(actual_error) as caught:
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
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"created": False, "alreadyExists": True, "commentId": "c2"}))
    result = provider(transport).add_bug_comment(2, "note", True, "key-2")
    assert result.status == "ALREADY_EXISTS"


def test_image_update_uses_bytes_and_safe_filename() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert b"picture.png" in request.content
        assert b"PNGDATA" in request.content
        assert b"C:\\private" not in request.content
        return httpx.Response(200, json={"updated": True, "bugId": 1, "version": "4"})

    result = provider(httpx.MockTransport(handle)).update_bug_steps_with_image(1, "full steps", b"PNGDATA", "picture.png", "image/png")
    assert result.updated
    with pytest.raises(ValueError):
        provider(httpx.MockTransport(handle)).update_bug_steps_with_image(1, "steps", b"x", "C:\\private\\x.png", "image/png")
