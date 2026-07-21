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
    TransportError,
    UnknownWriteResultError,
    ZentaoAuth,
    ZentaoEndpoints,
)
from zentao_ai.zentao.errors import (
    AmbiguousIdentityError,
    IdentityNotFoundError,
)


def provider(handler: httpx.MockTransport, **kwargs: object) -> HttpZentaoProvider:
    endpoints = kwargs.pop("endpoints", ZentaoEndpoints())
    assert isinstance(endpoints, ZentaoEndpoints)
    return HttpZentaoProvider(
        base_url="https://zentao.invalid",
        endpoints=endpoints,
        transport=handler,
        **kwargs,
    )


@pytest.mark.parametrize(
    ("requested", "match_type"),
    [
        (" \uff3a\uff28\uff2f\uff35\uff28\uff21\uff29\uff39\uff29\uff2e ", "account"),
        ("\u5468\u6d77\u97f3", "display_name"),
    ],
)
def test_query_user_bugs_resolves_member_pair_account_and_display_name_exactly(
    requested: str, match_type: str
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "memberPairs": {"zhouhaiyin": "\u5468\u6d77\u97f3"},
                "bugs": [
                    {
                        "id": 1,
                        "status": "active",
                        "assignedTo": {"account": "zhouhaiyin"},
                        "lastEditedDate": "v1",
                    }
                ],
                "page": 1,
                "limit": 20,
                "total": 1,
            },
        )
    )

    result = provider(
        transport, endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs")
    ).query_user_bugs(requested)

    assert [item.id for item in result.items] == [1]
    assert result.resolved_identity is not None
    assert result.resolved_identity.requested_identity == requested
    assert result.resolved_identity.resolved_account == "zhouhaiyin"
    assert result.resolved_identity.resolved_display_name == "\u5468\u6d77\u97f3"
    assert result.resolved_identity.match_type == match_type


def test_query_user_bugs_rejects_member_pair_without_an_exact_identity_match() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "memberPairs": {"zhouhaiyin": "\u5468\u6d77\u97f3"},
                "bugs": [],
                "page": 1,
                "limit": 20,
                "total": 0,
            },
        )
    )

    with pytest.raises(IdentityNotFoundError, match="^query_user_bugs: identity not found$"):
        provider(
            transport, endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs")
        ).query_user_bugs("zhou")


def test_query_user_bugs_rejects_ambiguous_member_pair_display_name() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "memberPairs": {
                    "zhouhaiyin": "\u5468\u6d77\u97f3",
                    "zhouhaiyin2": "\u5468\u6d77\u97f3",
                },
                "bugs": [],
                "page": 1,
                "limit": 20,
                "total": 0,
            },
        )
    )

    with pytest.raises(
        AmbiguousIdentityError, match="^query_user_bugs: ambiguous display name$"
    ):
        provider(
            transport, endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs")
        ).query_user_bugs("\u5468\u6d77\u97f3")


def test_query_user_bugs_retains_valid_official_rows_when_matching_rows_are_malformed() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api.php/v2/bugs/2":
            return httpx.Response(
                200,
                json={
                    "bug": {
                        "id": 2,
                        "status": "active",
                        "assignedTo": {"account": "zhouhaiyin"},
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "memberPairs": {"zhouhaiyin": "\u5468\u6d77\u97f3"},
                "bugs": [
                    {
                        "id": 1,
                        "status": "active",
                        "assignedTo": {"account": "zhouhaiyin"},
                        "lastEditedDate": "v1",
                    },
                    {
                        "id": 2,
                        "status": "active",
                        "assignedTo": {"account": "zhouhaiyin"},
                    },
                    {
                        "id": True,
                        "status": "active",
                        "assignedTo": {"account": "zhouhaiyin"},
                        "lastEditedDate": "v3",
                    },
                ],
                "page": 1,
                "limit": 20,
                "total": 3,
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("\u5468\u6d77\u97f3")

    assert [item.id for item in result.items] == [1]
    assert [failure.model_dump(by_alias=True) for failure in result.item_failures] == [
        {
            "bugId": "2",
            "code": "MISSING_STABLE_VERSION",
            "field": "version",
            "message": "missing stable version",
        },
        {
            "bugId": None,
            "code": "INVALID_BUG_CONTRACT",
            "field": "id",
            "message": "invalid bug contract",
        },
    ]
    assert result.coverage.returned == 1
    assert result.coverage.failed == 2
    assert result.coverage.complete is False
    assert result.coverage.total == -1
    assert result.coverage.pages is None


@pytest.mark.parametrize(
    ("detail_response", "message"),
    [
        (httpx.Response(422), "query_bug_detail status=422"),
        (httpx.Response(200, json={"bug": []}), "query_bug_detail: invalid bug contract"),
    ],
)
def test_query_user_bugs_does_not_isolate_detail_request_or_envelope_failures(
    detail_response: httpx.Response, message: str
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api.php/v2/bugs/2":
            return detail_response
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 2,
                        "status": "active",
                        "assignedTo": {"account": "zhouhaiyin"},
                    }
                ],
                "page": 1,
                "limit": 20,
                "total": 1,
            },
        )

    with pytest.raises(ContractError, match=f"^{message}$"):
        provider(
            httpx.MockTransport(handle),
            endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
        ).query_user_bugs("zhouhaiyin")


def test_login_endpoint_has_supported_default() -> None:
    assert ZentaoEndpoints().login == "/api.php/v2/users/login"


def test_official_product_endpoints_have_supported_defaults_and_aliases() -> None:
    endpoints = ZentaoEndpoints()
    assert endpoints.products == "/api.php/v2/products"
    assert endpoints.product_bugs == "/api.php/v2/products/{product_id}/bugs"
    assert (
        ZentaoEndpoints(
            products="/catalog", productBugs="/catalog/{product_id}/bugs"
        ).product_bugs
        == "/catalog/{product_id}/bugs"
    )


def test_official_bug_detail_uses_supported_route_envelope_and_stable_version() -> None:
    requests: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "bug": {
                    "id": 7,
                    "status": "active",
                    "title": "Official detail",
                    "openedBy": "alice",
                    "assignedTo": "bob",
                    "version": "fallback",
                    "lastEditedDate": "2026-07-17 09:30:00",
                }
            },
        )

    result = provider(httpx.MockTransport(handle)).query_bug_detail(7)

    assert requests == ["/api.php/v2/bugs/7"]
    assert result.creator is not None and result.creator.account == "alice"
    assert result.assignee == "bob"
    assert result.snapshot_version == "2026-07-17 09:30:00"


def test_custom_bug_detail_endpoint_preserves_flat_envelope() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"id": 8, "status": "open", "version": "custom-v1"}
        )
    )
    instance = HttpZentaoProvider(
        base_url="https://zentao.invalid",
        endpoints=ZentaoEndpoints(bugDetail="/custom/bugs/{bug_id}"),
        transport=transport,
    )

    assert instance.query_bug_detail(8).snapshot_version == "custom-v1"


def test_official_bug_history_adapts_actions_and_paginates_locally() -> None:
    requests: list[tuple[str, str]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append((request.url.path, request.url.query.decode()))
        return httpx.Response(
            200,
            json={
                "bug": {"id": 7, "status": "active"},
                "actions": {
                    "9": {
                        "id": "9",
                        "action": "opened",
                        "actor": "qa",
                        "apiToken": "discard",
                    },
                    "10": {
                        "id": "10",
                        "action": "edited",
                        "actor": "dev",
                        "idempotencyKey": "key-10",
                        "contentHash": "hash-10",
                    },
                    "11": {
                        "id": "11",
                        "action": "commented",
                        "actor": "qa",
                        "apiToken": "discard",
                    },
                },
            },
        )

    instance = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(bugHistory="/api.php/v2/bugs/{bug_id}"),
    )
    result = instance.query_bug_history(7, page=2, page_size=2)

    assert requests == [("/api.php/v2/bugs/7", "")]
    assert [(item.id, item.action, item.actor) for item in result.items] == [
        ("11", "commented", "qa")
    ]
    assert result.coverage.model_dump(by_alias=True) == {
        "page": 2,
        "pageSize": 2,
        "total": 3,
        "pages": 2,
        "returned": 0,
        "failed": 0,
        "complete": True,
    }
    assert "apiToken" not in result.items[0].raw


def test_official_bug_history_accepts_actions_list() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "bug": {"id": 7},
                "actions": [
                    {
                        "id": 9,
                        "action": "commented",
                        "actor": "qa",
                        "idempotencyKey": "key-9",
                        "contentHash": "hash-9",
                    }
                ],
            },
        )
    )
    instance = provider(
        transport,
        endpoints=ZentaoEndpoints(bugHistory="/api.php/v2/bugs/{bug_id}"),
    )

    result = instance.query_bug_history(7)

    assert result.items[0].id == 9
    assert result.items[0].action == "commented"
    assert result.items[0].actor == "qa"
    assert result.items[0].idempotency_key == "key-9"
    assert result.items[0].content_hash == "hash-9"


@pytest.mark.parametrize(
    "payload",
    [
        {"actions": []},
        {"bug": [], "actions": []},
        {"bug": {"id": 8}, "actions": []},
    ],
)
def test_official_bug_history_rejects_missing_or_wrong_bug_identity(
    payload: dict[str, object],
) -> None:
    instance = provider(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        endpoints=ZentaoEndpoints(bugHistory="/api.php/v2/bugs/{bug_id}"),
    )

    with pytest.raises(
        ContractError, match="^query_bug_history: invalid bug contract$"
    ):
        instance.query_bug_history(7)


@pytest.mark.parametrize(
    "payload",
    [
        {"bug": {"id": 7}},
        {"bug": {"id": 7}, "actions": "invalid"},
        {"bug": {"id": 7}, "actions": ["invalid"]},
        {"bug": {"id": 7}, "actions": {"9": "invalid"}},
    ],
)
def test_official_bug_history_rejects_missing_or_invalid_actions(
    payload: dict[str, object],
) -> None:
    instance = provider(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        endpoints=ZentaoEndpoints(bugHistory="/api.php/v2/bugs/{bug_id}"),
    )

    with pytest.raises(ContractError, match="^query_bug_history: invalid actions$"):
        instance.query_bug_history(7)


@pytest.mark.parametrize(
    "action",
    [
        {},
        {"unknown": 1},
        {"apiToken": "discard"},
        {"id": "", "action": "opened"},
        {"id": " ", "action": "opened"},
        {"id": True, "action": "opened"},
        {"id": 9, "action": ""},
        {"id": 9, "action": " "},
    ],
)
def test_official_bug_history_rejects_semantically_invalid_action_mappings(
    action: dict[str, object],
) -> None:
    instance = provider(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"bug": {"id": 7}, "actions": [action]}
            )
        ),
        endpoints=ZentaoEndpoints(bugHistory="/api.php/v2/bugs/{bug_id}"),
    )

    with pytest.raises(
        ContractError, match="^query_bug_history: invalid history contract$"
    ):
        instance.query_bug_history(7)


def test_official_bug_history_allows_missing_actor() -> None:
    instance = provider(
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "bug": {"id": 7},
                    "actions": [{"id": 9, "action": "opened"}],
                },
            )
        ),
        endpoints=ZentaoEndpoints(bugHistory="/api.php/v2/bugs/{bug_id}"),
    )

    assert instance.query_bug_history(7).items[0].actor is None


@pytest.mark.parametrize(
    "page,page_size",
    [(0, 20), (-1, 20), (1, 0), (1, -1), (1, 1001), (True, 20), (1, False)],
)
def test_query_bug_history_rejects_invalid_pagination_before_network(
    page: object, page_size: object
) -> None:
    requests = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json={"actions": []})

    instance = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(bugHistory="/api.php/v2/bugs/{bug_id}"),
    )
    with pytest.raises(ValueError, match="^invalid pagination$"):
        instance.query_bug_history(  # type: ignore[arg-type]
            7, page=page, page_size=page_size
        )

    assert requests == 0


@pytest.mark.parametrize(
    "status,error", [(401, AuthenticationError), (403, PermissionDeniedError)]
)
def test_official_bug_history_preserves_auth_and_permission_failures(
    status: int, error: type[Exception]
) -> None:
    instance = provider(
        httpx.MockTransport(lambda request: httpx.Response(status)),
        endpoints=ZentaoEndpoints(bugHistory="/api.php/v2/bugs/{bug_id}"),
    )

    with pytest.raises(error):
        instance.query_bug_history(7)


def test_custom_bug_history_endpoint_remains_supported() -> None:
    paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"items": [], "total": 0})

    instance = HttpZentaoProvider(
        base_url="https://zentao.invalid",
        endpoints=ZentaoEndpoints(bugHistory="/custom/bugs/{bug_id}/history"),
        transport=httpx.MockTransport(handle),
    )

    assert instance.query_bug_history(9).coverage.total == 0
    assert paths == ["/custom/bugs/9/history"]


@pytest.mark.parametrize(
    "page,page_size",
    [(0, 20), (-1, 20), (1, 0), (1, -1), (1, 1001), (True, 20), (1, False)],
)
def test_query_my_bugs_rejects_invalid_pagination_before_network(
    page: object, page_size: object
) -> None:
    requests = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json={"products": []})

    with pytest.raises(ValueError, match="^invalid pagination$"):
        provider(httpx.MockTransport(handle)).query_my_bugs(  # type: ignore[arg-type]
            page=page, page_size=page_size
        )

    assert requests == 0


def test_query_my_bugs_accepts_official_page_size_upper_bound() -> None:
    observed: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        observed.append(request.url.path)
        return httpx.Response(200, json={"products": [], "total": 0, "pages": 0})

    result = provider(httpx.MockTransport(handle)).query_my_bugs(page=1, page_size=1000)

    assert result.coverage.page_size == 1000
    assert observed == ["/api.php/v2/products"]


def test_query_my_bugs_with_username_uses_official_current_user_contract() -> None:
    observations: list[tuple[str, dict[str, str]]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        observations.append((request.url.path, dict(request.url.params)))
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 7,
                        "status": "active",
                        "assignedTo": "alice",
                        "lastEditedDate": "v7",
                    }
                ],
                "pager": {
                    "pageID": 1,
                    "recPerPage": 20,
                    "recTotal": 1,
                    "pageTotal": 1,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
        auth=ZentaoAuth(username=" alice ", apiToken="token"),
    ).query_my_bugs()

    assert [item.id for item in result.items] == [7]
    assert observations == [
        (
            "/api.php/v2/bugs",
            {
                "pageID": "1",
                "recPerPage": "20",
                "browseType": "assigntome",
            },
        )
    ]


def test_product_catalog_uses_official_pagination_and_preserves_valid_order() -> None:
    observations: list[tuple[str, dict[str, str]]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        observations.append((request.url.path, dict(request.url.params)))
        return httpx.Response(
            200,
            json={
                "products": [
                    {"id": 9, "name": " First "},
                    {"id": "", "name": "missing id"},
                    {"id": "10", "name": " Second ", "token": "discard"},
                    {"id": 11, "name": None},
                    "malformed",
                ]
            },
        )

    catalog = provider(httpx.MockTransport(handle))._load_product_catalog(
        page=2, page_size=5000
    )

    assert catalog == (("9", "First"), ("10", "Second"))
    assert observations == [
        (
            "/api.php/v2/products",
            {"browseType": "all", "recPerPage": "100", "pageID": "2"},
        )
    ]


@pytest.mark.parametrize(
    "payload",
    [[], {}, {"products": {}}, {"products": None}],
)
def test_product_catalog_rejects_malformed_envelopes(payload: object) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(ContractError, match="^product_catalog:"):
        provider(transport)._load_product_catalog()


def test_query_my_bugs_without_username_uses_exact_product_fallback_filter() -> None:
    observations: list[tuple[str, dict[str, str]]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        observations.append((request.url.path, dict(request.url.params)))
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={
                    "products": [{"id": 7, "name": "Ｓcope"}],
                    "total": 1,
                    "pages": 1,
                },
            )
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 3,
                        "status": "active",
                        "title": "title",
                        "steps": "steps",
                        "openedBy": "alice",
                        "assignedTo": "bob",
                        "lastEditedDate": "2026-07-16 09:00:00",
                    }
                ],
                "total": 1,
                "pages": 1,
            },
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("  scope  ",), page=1, page_size=5
    )

    assert observations[1] == (
        "/api.php/v2/products/7/bugs",
        {"browseType": "assigntome", "recPerPage": "5", "pageID": "1"},
    )
    bug = result.items[0]
    assert (bug.id, bug.creator.account, bug.assignee) == (3, "alice", "bob")
    assert (bug.title, bug.steps, bug.snapshot_version) == (
        "title",
        "steps",
        "2026-07-16 09:00:00",
    )
    assert result.coverage.page == 1 and result.coverage.page_size == 5
    assert result.coverage.total == 1


def test_query_my_bugs_unknown_and_ambiguous_scopes_are_incomplete() -> None:
    paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "products": [
                    {"id": 1, "name": "Same"},
                    {"id": 2, "name": " same "},
                ],
                "total": 2,
                "pages": 1,
            },
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("same", "missing")
    )

    assert paths == ["/api.php/v2/products"]
    assert result.items == ()
    assert result.coverage.total == -1 and result.coverage.pages is None
    assert (result.coverage.returned, result.coverage.failed, result.coverage.complete) == (
        0,
        0,
        False,
    )


def test_query_my_bugs_deduplicates_in_configured_scope_order_and_tracks_totals() -> (
    None
):
    def bug(identifier: object, title: str) -> dict[str, object]:
        return {
            "id": identifier,
            "status": "open",
            "title": title,
            "lastEditedDate": "2026-07-16",
        }

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={
                    "products": [
                        {"id": "a", "name": "Alpha"},
                        {"id": "b", "name": "Beta"},
                    ],
                    "total": 2,
                    "pages": 1,
                },
            )
        if "/b/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "bugs": [bug(" 7 ", "first"), bug(8, "eight")],
                    "total": 2,
                    "pages": 1,
                },
            )
        return httpx.Response(
            200,
            json={
                "bugs": [bug(7, "duplicate"), bug(9, "nine")],
                "total": 2,
                "pages": 1,
            },
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("Beta", "Alpha"), page_size=10
    )

    assert [(str(item.id).strip(), item.title) for item in result.items] == [
        ("7", "first"),
        ("8", "eight"),
        ("9", "nine"),
    ]
    assert result.coverage.total == 3


def test_query_my_bugs_applies_page_to_global_multi_product_union() -> None:
    requested: list[tuple[str, str]] = []

    def item(identifier: int) -> dict[str, object]:
        return {"id": identifier, "status": "open", "lastEditedDate": "v"}

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={
                    "products": [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
                    "total": 2,
                    "pages": 1,
                },
            )
        product = request.url.path.split("/")[-2]
        product_page = request.url.params["pageID"]
        requested.append((product, product_page))
        values = {
            ("a", "1"): [1, 2],
            ("a", "2"): [3],
            ("b", "1"): [4, 5],
            ("b", "2"): [6],
        }
        bugs = [item(value) for value in values[(product, product_page)]]
        return httpx.Response(200, json={"bugs": bugs, "total": 3, "pages": 2})

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("A", "B"), page=2, page_size=2
    )

    assert [bug.id for bug in result.items] == [3, 4]
    assert len(result.items) <= 2
    assert requested == [("a", "1"), ("a", "2"), ("b", "1")]
    assert result.coverage.total == -1 and result.coverage.pages is None


def test_query_my_bugs_reports_exact_deduplicated_total_only_after_full_union() -> None:
    def item(identifier: int) -> dict[str, object]:
        return {"id": identifier, "status": "open", "lastEditedDate": "v"}

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={
                    "products": [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
                    "total": 2,
                    "pages": 1,
                },
            )
        values = [1, 2] if "/a/" in request.url.path else [2, 3]
        return httpx.Response(
            200,
            json={"bugs": [item(value) for value in values], "total": 2, "pages": 1},
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("A", "B"), page=1, page_size=3
    )

    assert [bug.id for bug in result.items] == [1, 2, 3]
    assert result.coverage.total == 3 and result.coverage.pages == 1


def test_query_my_bugs_overlap_exhausted_by_empty_page_has_exact_total() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={
                    "products": [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
                    "total": 2,
                    "pages": 1,
                },
            )
        if request.url.params["pageID"] == "2":
            return httpx.Response(200, json={"bugs": []})
        identifiers = [1, 2] if "/a/" in request.url.path else [2, 3]
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {"id": value, "status": "open", "lastEditedDate": "v"}
                    for value in identifiers
                ]
            },
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("A", "B"), page_size=10
    )
    assert len(result.items) == 3
    assert result.coverage.total == 3 and result.coverage.pages == 1


def test_query_my_bugs_resolves_scope_from_later_catalog_page() -> None:
    catalog_pages: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            page_id = request.url.params["pageID"]
            catalog_pages.append(page_id)
            if page_id == "1":
                return httpx.Response(
                    200,
                    json={
                        "products": [
                            {"id": index, "name": f"P{index}"} for index in range(100)
                        ]
                    },
                )
            if page_id == "2":
                return httpx.Response(
                    200, json={"products": [{"id": 101, "name": "Later"}]}
                )
            return httpx.Response(200, json={"products": []})
        return httpx.Response(
            200,
            json={
                "bugs": [{"id": 9, "status": "open", "lastEditedDate": "v"}],
                "total": 1,
                "pages": 1,
            },
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("Later",), page_size=20
    )
    assert catalog_pages == ["1", "2", "3"]
    assert [bug.id for bug in result.items] == [9]
    assert result.coverage.total == 1


def test_query_my_bugs_continues_capped_product_without_totals_before_later_product() -> (
    None
):
    bug_requests: list[tuple[str, str]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            if request.url.params["pageID"] == "1":
                return httpx.Response(
                    200,
                    json={
                        "products": [
                            {"id": "a", "name": "A"},
                            {"id": "b", "name": "B"},
                        ],
                        "total": 2,
                        "pages": 1,
                    },
                )
            return httpx.Response(200, json={"products": []})
        product = request.url.path.split("/")[-2]
        product_page = request.url.params["pageID"]
        bug_requests.append((product, product_page))
        values = {("a", "1"): [1], ("a", "2"): [2], ("a", "3"): []}
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {"id": value, "status": "open", "lastEditedDate": "v"}
                    for value in values.get((product, product_page), [3])
                ]
            },
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("A", "B"), page=1, page_size=2
    )

    assert [bug.id for bug in result.items] == [1, 2]
    assert bug_requests == [("a", "1"), ("a", "2")]
    assert result.coverage.total == -1 and result.coverage.pages is None


def test_query_my_bugs_short_page_with_remaining_total_preserves_global_order() -> None:
    bug_requests: list[tuple[str, str]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={
                    "products": [
                        {"id": "a", "name": "A"},
                        {"id": "b", "name": "B"},
                    ],
                    "total": 2,
                    "pages": 1,
                },
            )
        product = request.url.path.split("/")[-2]
        product_page = request.url.params["pageID"]
        bug_requests.append((product, product_page))
        value = 1 if product_page == "1" else 2
        return httpx.Response(
            200,
            json={
                "bugs": [{"id": value, "status": "open", "lastEditedDate": "v"}],
                "total": 2,
                "pages": 2,
            },
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("A", "B"), page=2, page_size=1
    )

    assert [bug.id for bug in result.items] == [2]
    assert bug_requests == [("a", "1"), ("a", "2")]
    assert result.coverage.total == -1


def test_query_my_bugs_does_not_resolve_unique_scope_from_capped_catalog_page() -> None:
    paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        page = request.url.params["pageID"]
        if page == "1":
            return httpx.Response(200, json={"products": [{"id": 1, "name": "Same"}]})
        if page == "2":
            return httpx.Response(200, json={"products": [{"id": 2, "name": " same "}]})
        return httpx.Response(200, json={"products": []})

    result = provider(httpx.MockTransport(handle)).query_my_bugs(scope_names=("same",))

    assert paths == ["/api.php/v2/products"] * 3
    assert result.items == ()
    assert result.coverage.total == -1 and result.coverage.pages is None


def test_query_my_bugs_premature_empty_product_page_is_incomplete_and_order_safe() -> (
    None
):
    bug_products: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={
                    "products": [
                        {"id": "a", "name": "A"},
                        {"id": "b", "name": "B"},
                    ],
                    "total": 2,
                    "pages": 1,
                },
            )
        product = request.url.path.split("/")[-2]
        bug_products.append(product)
        if request.url.params["pageID"] == "1":
            return httpx.Response(
                200,
                json={
                    "bugs": [{"id": 1, "status": "open", "lastEditedDate": "v"}],
                    "total": 3,
                    "pages": 2,
                },
            )
        return httpx.Response(200, json={"bugs": [], "total": 3, "pages": 2})

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("A", "B"), page_size=5
    )

    assert [bug.id for bug in result.items] == [1]
    assert bug_products == ["a", "a"]
    assert result.coverage.total == -1 and result.coverage.pages is None


def test_query_my_bugs_premature_empty_catalog_page_blocks_scope_resolution() -> None:
    paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.params["pageID"] == "1":
            return httpx.Response(
                200,
                json={
                    "products": [{"id": 1, "name": "A"}],
                    "total": 2,
                    "pages": 2,
                },
            )
        return httpx.Response(200, json={"products": [], "total": 2, "pages": 2})

    result = provider(httpx.MockTransport(handle)).query_my_bugs(scope_names=("A",))

    assert paths == ["/api.php/v2/products", "/api.php/v2/products"]
    assert result.items == ()
    assert result.coverage.total == -1 and result.coverage.pages is None


def test_query_my_bugs_conflicting_product_metadata_stays_incomplete_after_empty() -> (
    None
):
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={
                    "products": [{"id": "a", "name": "A"}],
                    "total": 1,
                    "pages": 1,
                },
            )
        page = request.url.params["pageID"]
        if page == "1":
            return httpx.Response(
                200,
                json={
                    "bugs": [{"id": 1, "status": "open", "lastEditedDate": "v"}],
                    "total": 2,
                    "pages": 2,
                },
            )
        if page == "2":
            return httpx.Response(
                200,
                json={
                    "bugs": [{"id": 2, "status": "open", "lastEditedDate": "v"}],
                    "total": 3,
                    "pages": 3,
                },
            )
        return httpx.Response(200, json={"bugs": []})

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("A",), page_size=5
    )

    assert [bug.id for bug in result.items] == [1, 2]
    assert result.coverage.total == -1 and result.coverage.pages is None


def test_query_my_bugs_conflicting_catalog_metadata_stays_incomplete_after_empty() -> (
    None
):
    paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        page = request.url.params["pageID"]
        if page == "1":
            return httpx.Response(
                200,
                json={
                    "products": [{"id": 1, "name": "A"}],
                    "total": 2,
                    "pages": 2,
                },
            )
        if page == "2":
            return httpx.Response(
                200,
                json={
                    "products": [{"id": 2, "name": "B"}],
                    "total": 3,
                    "pages": 3,
                },
            )
        return httpx.Response(200, json={"products": []})

    result = provider(httpx.MockTransport(handle)).query_my_bugs(scope_names=("A",))

    assert paths == ["/api.php/v2/products"] * 3
    assert result.items == ()
    assert result.coverage.total == -1 and result.coverage.pages is None


def test_query_my_bugs_invalid_present_product_metadata_stays_incomplete_after_empty() -> (
    None
):
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200,
                json={"products": [{"id": "a", "name": "A"}], "total": 1, "pages": 1},
            )
        if request.url.params["pageID"] == "1":
            return httpx.Response(
                200,
                json={
                    "bugs": [{"id": 1, "status": "open", "lastEditedDate": "v"}],
                    "total": "invalid",
                    "pages": -1,
                },
            )
        return httpx.Response(200, json={"bugs": []})

    result = provider(httpx.MockTransport(handle)).query_my_bugs(
        scope_names=("A",), page_size=5
    )

    assert [bug.id for bug in result.items] == [1]
    assert result.coverage.total == -1 and result.coverage.pages is None


def test_query_my_bugs_invalid_present_catalog_metadata_stays_incomplete_after_empty() -> (
    None
):
    paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.params["pageID"] == "1":
            return httpx.Response(
                200,
                json={
                    "products": [{"id": 1, "name": "A"}],
                    "total": "invalid",
                    "pages": -1,
                },
            )
        return httpx.Response(200, json={"products": []})

    result = provider(httpx.MockTransport(handle)).query_my_bugs(scope_names=("A",))

    assert paths == ["/api.php/v2/products", "/api.php/v2/products"]
    assert result.items == ()
    assert result.coverage.total == -1 and result.coverage.pages is None


def test_query_my_bugs_uses_nonblank_version_fallback() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200, json={"products": [{"id": 1, "name": "A"}], "total": 1, "pages": 1}
            )
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {"id": 1, "status": "open", "lastEditedDate": " ", "version": 4}
                ],
                "total": 1,
                "pages": 1,
            },
        )

    result = provider(httpx.MockTransport(handle)).query_my_bugs(scope_names=("A",))
    assert result.items[0].snapshot_version == "4"


@pytest.mark.parametrize("payload", [{}, {"bugs": {}}, {"bugs": ["raw-secret"]}])
def test_query_my_bugs_rejects_malformed_bugs_envelope_without_raw_values(
    payload: object,
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200, json={"products": [{"id": 1, "name": "A"}], "total": 1, "pages": 1}
            )
        return httpx.Response(200, json=payload)

    with pytest.raises(ContractError) as caught:
        provider(httpx.MockTransport(handle)).query_my_bugs(scope_names=("A",))
    assert str(caught.value) == "query_my_bugs: invalid bugs contract"
    assert "raw-secret" not in str(caught.value)


def test_query_my_bugs_missing_stable_version_is_sanitized() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(
                200, json={"products": [{"id": 1, "name": "A"}], "total": 1, "pages": 1}
            )
        return httpx.Response(
            200,
            json={"bugs": [{"id": "raw-id", "status": "open", "title": "raw-title"}]},
        )

    with pytest.raises(ContractError) as caught:
        provider(httpx.MockTransport(handle)).query_my_bugs(scope_names=("A",))
    assert str(caught.value) == "query_my_bugs: missing stable version"
    assert "raw-id" not in str(caught.value) and "raw-title" not in str(caught.value)


@pytest.mark.parametrize(
    "login_payload",
    [{"token": "session-token"}, {"data": {"token": "session-token"}}],
)
def test_password_login_token_envelopes_are_used_for_subsequent_request(
    login_payload: dict[str, object],
) -> None:
    observations: list[tuple[str, str | None, dict[str, object] | None]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        observations.append(
            (request.url.path, request.headers.get("Authorization"), body)
        )
        if request.url.path == "/api.php/v2/users/login":
            return httpx.Response(200, json=login_payload)
        return httpx.Response(200, json={"items": []})

    instance = provider(
        httpx.MockTransport(handle),
        auth=ZentaoAuth(username="alice", password=SecretStr("password-secret")),
    )
    instance.query_user_bugs("alice")

    assert observations == [
        (
            "/api.php/v2/users/login",
            None,
            {"account": "alice", "password": "password-secret"},
        ),
        ("/api/bugs/user/alice", "Bearer session-token", None),
    ]


@pytest.mark.parametrize(
    "login_payload",
    [{}, {"token": "  "}, {"token": 7}, {"data": {}}, {"data": {"token": None}}],
)
def test_password_login_rejects_invalid_tokens_without_leaking_secrets(
    login_payload: dict[str, object],
) -> None:
    raw_marker = "raw-payload-marker"

    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={**login_payload, "marker": raw_marker})

    instance = provider(
        httpx.MockTransport(handle),
        auth=ZentaoAuth(username="alice", password=SecretStr("password-secret")),
    )
    with pytest.raises(ContractError) as caught:
        instance.query_my_bugs()

    assert str(caught.value) == "login: missing token"
    rendered = f"{caught.value!r} {instance!r}"
    assert "password-secret" not in rendered
    assert "session-token" not in rendered
    assert raw_marker not in rendered


def test_password_login_transport_error_is_sanitized_without_retry() -> None:
    calls = 0
    secret_marker = "password-and-raw-marker"

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError(secret_marker, request=request)

    instance = provider(
        httpx.MockTransport(handle),
        auth=ZentaoAuth(username="alice", password=SecretStr(secret_marker)),
    )
    with pytest.raises(TransportError) as caught:
        instance.query_my_bugs()

    assert calls == 1
    assert str(caught.value) == "login: transport failure"
    assert secret_marker not in repr(caught.value)


def test_password_auth_reauthenticates_only_once_after_repeated_unauthorized() -> None:
    login_calls = 0
    query_calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal login_calls, query_calls
        if request.url.path == "/api.php/v2/users/login":
            login_calls += 1
            return httpx.Response(200, json={"token": f"session-token-{login_calls}"})
        query_calls += 1
        return httpx.Response(401, json={"raw": "must-not-leak"})

    instance = provider(
        httpx.MockTransport(handle),
        auth=ZentaoAuth(username="alice", password=SecretStr("password-secret")),
    )

    with pytest.raises(AuthenticationError) as caught:
        instance.query_my_bugs()

    assert login_calls == 2
    assert query_calls == 2
    rendered = repr(caught.value)
    assert "password-secret" not in rendered
    assert "session-token" not in rendered
    assert "must-not-leak" not in rendered


def test_password_auth_retries_with_refreshed_bearer_after_unauthorized() -> None:
    login_calls = 0
    query_headers: list[str | None] = []

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal login_calls
        if request.url.path == "/api.php/v2/users/login":
            login_calls += 1
            return httpx.Response(200, json={"token": f"session-token-{login_calls}"})
        query_headers.append(request.headers.get("Authorization"))
        if len(query_headers) == 1:
            return httpx.Response(401)
        return httpx.Response(200, json={"items": []})

    instance = provider(
        httpx.MockTransport(handle),
        auth=ZentaoAuth(username="alice", password=SecretStr("password-secret")),
    )

    instance.query_user_bugs("alice")

    assert login_calls == 2
    assert query_headers == ["Bearer session-token-1", "Bearer session-token-2"]


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
                "pages": 2,
            },
        )

    result = provider(httpx.MockTransport(handle)).query_user_bugs("alice", page=2)
    assert result.items[0].snapshot_version == "3"
    assert result.coverage.total == 21


def test_query_user_bugs_adapts_official_bugs_envelope() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 2537,
                        "title": "【AI建站】First",
                        "status": "active",
                        "openedBy": "alice",
                        "assignedTo": "alice",
                        "lastEditedDate": "2026-07-17 09:30:00",
                    },
                    {
                        "id": 3397,
                        "title": "【AI建站】Second",
                        "status": "active",
                        "openedBy": "bob",
                        "assignedTo": "alice",
                        "lastEditedDate": "2026-07-17 10:30:00",
                    },
                ],
                "page": 1,
                "pageSize": 20,
                "total": 2,
                "pages": 1,
            },
        )

    result = provider(httpx.MockTransport(handle)).query_user_bugs("alice")

    assert [item.id for item in result.items] == [2537, 3397]
    assert [item.title for item in result.items] == [
        "【AI建站】First",
        "【AI建站】Second",
    ]
    assert [item.assignee for item in result.items] == ["alice", "alice"]
    assert [item.snapshot_version for item in result.items] == [
        "2026-07-17 09:30:00",
        "2026-07-17 10:30:00",
    ]
    assert result.coverage.page == 1
    assert result.coverage.page_size == 20
    assert result.coverage.total == 2
    assert result.coverage.pages == 1
    assert len(requests) == 1
    assert requests[0].url.path == "/api/bugs/user/alice"
    assert dict(requests[0].url.params) == {"page": "1", "pageSize": "20"}


def test_query_user_bugs_adapts_observed_assignee_map_and_pager() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert dict(request.url.params) == {
            "pageID": "1",
            "recPerPage": "20",
        }
        return httpx.Response(
            200,
            json={
                "bugs": {
                    "3397": {
                        "id": 3397,
                        "title": "銆愮珯鐐瑰悗鍙般€慡econd",
                        "status": "active",
                        "openedBy": {"account": "qa"},
                        "assignedTo": {"account": "alice"},
                        "lastEditedDate": "2026-07-17 10:30:00",
                    },
                    "2537": {
                        "id": 2537,
                        "title": "銆怉I寤虹珯銆慏irst",
                        "status": "active",
                        "openedBy": {"account": "qa"},
                        "assignedTo": {"account": "alice"},
                        "lastEditedDate": "2026-07-17 09:30:00",
                    },
                },
                "pager": {
                    "pageID": 1,
                    "recPerPage": 20,
                    "recTotal": 2,
                    "pageTotal": 1,
                },
            },
        )

    endpoints = ZentaoEndpoints(userBugs="/api.php/v2/bugs")
    result = provider(
        httpx.MockTransport(handle),
        endpoints=endpoints,
        auth=ZentaoAuth(username="alice", apiToken="token"),
    ).query_user_bugs("alice")

    assert [item.id for item in result.items] == [2537, 3397]
    assert [
        item.creator.account if item.creator else None for item in result.items
    ] == [
        "qa",
        "qa",
    ]
    assert [item.assignee for item in result.items] == ["alice", "alice"]
    assert result.coverage.page == 1
    assert result.coverage.page_size == 20
    assert result.coverage.total == 2
    assert result.coverage.pages == 1


def test_query_user_bugs_filters_official_collection_by_assignee_account() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api.php/v2/bugs"
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 1,
                        "status": "active",
                        "title": "designer",
                        "openedBy": {"account": "qa"},
                        "assignedTo": {"account": "xuli"},
                        "lastEditedDate": "2026-07-20 09:00:00",
                    },
                    {
                        "id": 2,
                        "status": "active",
                        "title": "other",
                        "openedBy": {"account": "qa"},
                        "assignedTo": {"account": "other"},
                        "lastEditedDate": "2026-07-20 09:01:00",
                    },
                ],
                "page": 1,
                "limit": 20,
                "total": 2,
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
        auth=ZentaoAuth(username="weiwenting", apiToken="token"),
    ).query_user_bugs("xuli")

    assert [item.id for item in result.items] == [1]
    assert result.items[0].assignee == "xuli"
    assert result.coverage.total == 1
    assert result.coverage.pages == 1


def test_query_user_bugs_matches_official_assignee_real_name() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api.php/v2/bugs"
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 1,
                        "status": "active",
                        "title": "designer",
                        "openedBy": {"account": "qa"},
                        "assignedTo": {"account": "xuli", "realname": "许立"},
                        "lastEditedDate": "2026-07-20 09:00:00",
                    },
                    {
                        "id": 2,
                        "status": "active",
                        "title": "other",
                        "openedBy": {"account": "qa"},
                        "assignedTo": {"account": "other", "realname": "其他人"},
                        "lastEditedDate": "2026-07-20 09:01:00",
                    },
                ],
                "page": 1,
                "limit": 20,
                "total": 2,
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
        auth=ZentaoAuth(username="weiwenting", apiToken="token"),
    ).query_user_bugs("许立")

    assert [item.id for item in result.items] == [1]
    assert result.items[0].assignee == "xuli"
    assert result.coverage.total == 1
    assert result.coverage.pages == 1


def test_query_user_bugs_resolves_member_pairs_display_name_to_account() -> None:
    requested_paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/api.php/v2/bugs/7":
            return httpx.Response(
                200,
                json={
                    "bug": {
                        "id": 7,
                        "status": "active",
                        "title": "verified detail",
                        "assignedTo": {"account": "xuli"},
                        "lastEditedDate": "detail-v1",
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "memberPairs": {"xuli": "许立", "other": "其他人"},
                "bugs": [
                    {
                        "id": 7,
                        "status": "active",
                        "title": "unstable list row",
                        "openedBy": {"account": "qa"},
                        "assignedTo": {"account": "xuli"},
                    },
                    {
                        "id": 8,
                        "status": "active",
                        "title": "other",
                        "openedBy": {"account": "qa"},
                        "assignedTo": {"account": "other"},
                        "lastEditedDate": "v8",
                    },
                ],
                "page": 1,
                "limit": 20,
                "total": 2,
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("许立")

    assert requested_paths == ["/api.php/v2/bugs", "/api.php/v2/bugs/7"]
    assert [item.id for item in result.items] == [7]
    assert result.items[0].assignee == "xuli"
    assert result.coverage.total == 1
    assert result.coverage.pages == 1


def test_query_user_bugs_ignores_unmatched_bug_without_stable_version() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 2,
                        "status": "active",
                        "assignedTo": {"account": "other"},
                    },
                    {
                        "id": 1,
                        "status": "active",
                        "assignedTo": {"account": "xuli"},
                        "lastEditedDate": "2026-07-20 09:00:00",
                    },
                ]
            },
        )
    )

    result = provider(
        transport, endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs")
    ).query_user_bugs("xuli")

    assert [item.id for item in result.items] == [1]


def test_query_user_bugs_scans_complete_official_collection_before_filtering() -> None:
    requested_pages: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_page = int(request.url.params["pageID"])
        requested_pages.append(requested_page)
        bug_id, assignee = (1, "other") if requested_page == 1 else (2, "xuli")
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": bug_id,
                        "status": "active",
                        "assignedTo": {"account": assignee},
                        "lastEditedDate": f"v{bug_id}",
                    }
                ],
                "pager": {
                    "pageID": requested_page,
                    "recPerPage": 1,
                    "recTotal": 2,
                    "pageTotal": 2,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli", page_size=1)

    assert requested_pages == [1, 2]
    assert [item.id for item in result.items] == [2]
    assert result.coverage.total == 1
    assert result.coverage.pages == 1


def test_query_user_bugs_scans_until_empty_when_official_metadata_is_missing() -> None:
    requested_pages: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_page = int(request.url.params["pageID"])
        requested_pages.append(requested_page)
        rows = {
            1: [
                {
                    "id": 1,
                    "status": "active",
                    "assignedTo": "other",
                    "lastEditedDate": "v1",
                }
            ],
            2: [
                {
                    "id": 2,
                    "status": "active",
                    "assignedTo": "xuli",
                    "lastEditedDate": "v2",
                }
            ],
        }.get(requested_page, [])
        return httpx.Response(200, json={"bugs": rows})

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli", page_size=1)

    assert requested_pages == [1, 2, 3]
    assert [item.id for item in result.items] == [2]
    assert result.coverage.total == 1
    assert result.coverage.pages == 1


def test_query_user_bugs_enriches_matching_row_from_verified_detail() -> None:
    requested_paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/api.php/v2/bugs/7":
            return httpx.Response(
                200,
                json={
                    "bug": {
                        "id": 7,
                        "status": "active",
                        "title": "verified detail",
                        "assignedTo": {"account": "xuli"},
                        "lastEditedDate": "detail-v1",
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 7,
                        "status": "active",
                        "title": "unstable list row",
                        "assignedTo": {"account": "xuli"},
                    }
                ],
                "pager": {
                    "pageID": 1,
                    "recPerPage": 20,
                    "recTotal": 1,
                    "pageTotal": 1,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli")

    assert requested_paths == ["/api.php/v2/bugs", "/api.php/v2/bugs/7"]
    assert [item.id for item in result.items] == [7]
    assert result.items[0].title == "verified detail"
    assert result.items[0].snapshot_version == "detail-v1"
    assert result.coverage.total == 1


def test_query_user_bugs_records_matching_unstable_row_without_id() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "bugs": [{"status": "active", "assignedTo": "xuli"}],
                "pager": {
                    "pageID": 1,
                    "recPerPage": 20,
                    "recTotal": 1,
                    "pageTotal": 1,
                },
            },
        )
    )

    result = provider(
        transport, endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs")
    ).query_user_bugs("xuli")

    assert result.items == ()
    assert [failure.model_dump(by_alias=True) for failure in result.item_failures] == [
        {
            "bugId": None,
            "code": "INVALID_BUG_CONTRACT",
            "field": "id",
            "message": "invalid bug contract",
        }
    ]
    assert result.coverage.failed == 1
    assert result.coverage.complete is False


@pytest.mark.parametrize(
    ("detail_bug", "code", "field"),
    [
        (
            {
                "id": 7,
                "status": "active",
                "assignedTo": "other",
                "lastEditedDate": "detail-v1",
            },
            "INVALID_BUG_CONTRACT",
            None,
        ),
        (
            {"id": 7, "status": "active", "assignedTo": "xuli"},
            "MISSING_STABLE_VERSION",
            "version",
        ),
    ],
)
def test_query_user_bugs_records_unverified_detail(
    detail_bug: dict[str, object], code: str, field: str | None
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api.php/v2/bugs/7":
            return httpx.Response(200, json={"bug": detail_bug})
        return httpx.Response(
            200,
            json={
                "bugs": [{"id": 7, "status": "active", "assignedTo": "xuli"}],
                "pager": {
                    "pageID": 1,
                    "recPerPage": 20,
                    "recTotal": 1,
                    "pageTotal": 1,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli")

    assert result.items == ()
    assert result.item_failures[0].bug_id == "7"
    assert result.item_failures[0].code == code
    assert result.item_failures[0].field == field
    assert result.coverage.complete is False


def test_query_user_bugs_marks_repeated_official_page_incomplete() -> None:
    requested_pages: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_page = int(request.url.params["pageID"])
        requested_pages.append(requested_page)
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 1,
                        "status": "active",
                        "assignedTo": "xuli",
                        "lastEditedDate": "v1",
                    }
                ],
                "pager": {
                    "pageID": requested_page,
                    "recPerPage": 1,
                    "recTotal": 2,
                    "pageTotal": 2,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli", page_size=1)

    assert requested_pages == [1, 2]
    assert [item.id for item in result.items] == [1]
    assert result.coverage.total == -1
    assert result.coverage.pages is None


def test_query_user_bugs_marks_contradictory_official_pager_incomplete() -> None:
    requested_pages: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_page = int(request.url.params["pageID"])
        requested_pages.append(requested_page)
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": requested_page,
                        "status": "active",
                        "assignedTo": "xuli",
                        "lastEditedDate": f"v{requested_page}",
                    }
                ],
                "pager": {
                    "pageID": requested_page,
                    "recPerPage": 1,
                    "recTotal": 2 if requested_page == 1 else 3,
                    "pageTotal": 2 if requested_page == 1 else 3,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli", page=2, page_size=1)

    assert requested_pages == [1, 2]
    assert [item.id for item in result.items] == [2]
    assert result.coverage.total == -1
    assert result.coverage.pages is None


def test_query_user_bugs_does_not_fallback_from_malformed_present_pager() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 1,
                        "status": "active",
                        "assignedTo": "xuli",
                        "lastEditedDate": "v1",
                    }
                ],
                "pager": None,
                "page": 1,
                "limit": 20,
                "total": 1,
            },
        )
    )

    result = provider(
        transport,
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli")

    assert [item.id for item in result.items] == [1]
    assert result.coverage.total == -1
    assert result.coverage.pages is None


def test_query_user_bugs_marks_cross_page_id_overlap_incomplete() -> None:
    requested_pages: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_page = int(request.url.params["pageID"])
        requested_pages.append(requested_page)
        ids = [1, 2] if requested_page == 1 else [2, 3]
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": bug_id,
                        "status": "active",
                        "assignedTo": "xuli",
                        "lastEditedDate": f"v{bug_id}",
                    }
                    for bug_id in ids
                ],
                "pager": {
                    "pageID": requested_page,
                    "recPerPage": 2,
                    "recTotal": 4,
                    "pageTotal": 2,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli", page=2, page_size=2)

    assert requested_pages == [1, 2]
    assert [item.id for item in result.items] == [3]
    assert result.coverage.total == -1
    assert result.coverage.pages is None


def test_query_user_bugs_marks_max_page_exhaustion_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(HttpZentaoProvider, "_MAX_USER_BUG_PAGES", 2)
    requested_pages: list[int] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_page = int(request.url.params["pageID"])
        requested_pages.append(requested_page)
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": requested_page,
                        "status": "active",
                        "assignedTo": "xuli",
                        "lastEditedDate": f"v{requested_page}",
                    }
                ],
                "pager": {
                    "pageID": requested_page,
                    "recPerPage": 1,
                    "recTotal": 3,
                    "pageTotal": 3,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli", page=2, page_size=1)

    assert requested_pages == [1, 2]
    assert [item.id for item in result.items] == [2]
    assert result.coverage.total == -1
    assert result.coverage.pages is None


def test_query_user_bugs_keeps_filtered_items_with_contradictory_metadata() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "bugs": {
                    "1": {
                        "id": 1,
                        "status": "active",
                        "assignedTo": {"account": "xuli"},
                        "lastEditedDate": "2026-07-20 09:00:00",
                    },
                    "2": {
                        "id": 2,
                        "status": "active",
                        "assignedTo": {"account": "other"},
                        "lastEditedDate": "2026-07-20 09:01:00",
                    },
                },
                "pager": {
                    "pageID": 1,
                    "recPerPage": 20,
                    "recTotal": 1,
                    "pageTotal": 0,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("xuli")

    assert [item.id for item in result.items] == [1]
    assert result.coverage.total == -1
    assert result.coverage.pages is None


def test_query_user_bugs_transmits_only_nonempty_scope_names() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"bugs": [], "pager": {}})

    endpoints = ZentaoEndpoints(userBugs="/api.php/v2/bugs")
    instance = provider(
        httpx.MockTransport(handle),
        endpoints=endpoints,
        auth=ZentaoAuth(username="alice", apiToken="token"),
    )
    instance.query_user_bugs("alice", scope_names=())
    instance.query_user_bugs("alice", scope_names=("Site", "API"))

    assert "scopeNames" not in requests[0].url.params
    assert requests[1].url.params.get_list("scopeNames") == ["Site", "API"]


def test_official_collection_uses_page_id_and_records_per_page() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 7,
                        "status": "active",
                        "assignedTo": "alice",
                        "lastEditedDate": "v7",
                    }
                ],
                "pager": {
                    "pageID": 1,
                    "recPerPage": 20,
                    "recTotal": 1,
                    "pageTotal": 1,
                },
            },
        )

    endpoints = ZentaoEndpoints(userBugs="/api.php/v2/bugs")
    instance = provider(
        httpx.MockTransport(handle),
        endpoints=endpoints,
        auth=ZentaoAuth(username="alice", apiToken="token"),
    )
    result = instance.query_user_bugs("alice", scope_names=())

    assert [item.id for item in result.items] == [7]
    assert requests[0].url.path == "/api.php/v2/bugs"
    assert dict(requests[0].url.params) == {
        "pageID": "1",
        "recPerPage": "20",
    }


def test_official_personal_collection_uses_exact_assignee_browse_type() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 7,
                        "status": "active",
                        "assignedTo": "alice",
                        "lastEditedDate": "v7",
                    }
                ],
                "pager": {
                    "pageID": 1,
                    "recPerPage": 20,
                    "recTotal": 1,
                    "pageTotal": 1,
                },
            },
        )

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs"),
    ).query_user_bugs("alice", browse_type="assigntome")

    assert [item.id for item in result.items] == [7]
    assert dict(requests[0].url.params) == {
        "pageID": "1",
        "recPerPage": "20",
        "browseType": "assigntome",
    }


@pytest.mark.parametrize("username", ["alice", None])
def test_official_collection_is_used_for_any_requested_account(
    username: str | None,
) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"bugs": []})

    endpoints = ZentaoEndpoints(userBugs="/api.php/v2/bugs")
    instance = provider(
        httpx.MockTransport(handle),
        endpoints=endpoints,
        auth=ZentaoAuth(username=username, apiToken="token"),
    )
    instance.query_user_bugs("bob", scope_names=("Site",))

    assert requests[0].url.path == "/api.php/v2/bugs"
    assert requests[0].url.params.get_list("scopeNames") == ["Site"]
    assert requests[0].url.params["recPerPage"] == "20"
    assert "browseType" not in requests[0].url.params


def test_custom_user_bugs_endpoint_is_preserved_with_requested_user_and_scopes() -> (
    None
):
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"items": []})

    endpoints = ZentaoEndpoints(userBugs="/custom/users/{user}/assigned")
    instance = provider(
        httpx.MockTransport(handle),
        endpoints=endpoints,
        auth=ZentaoAuth(username="alice", apiToken="token"),
    )
    instance.query_user_bugs("bob", scope_names=("Site", "API"), page=2)

    assert requests[0].url.path == "/custom/users/bob/assigned"
    assert requests[0].url.params.get_list("scopeNames") == ["Site", "API"]
    assert requests[0].url.params["page"] == "2"
    assert requests[0].url.params["pageSize"] == "20"
    assert "browseType" not in requests[0].url.params


def test_query_user_bugs_rejects_unknown_envelope() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"items": []})
    )

    with pytest.raises(ContractError, match="^query_user_bugs: invalid items$"):
        provider(
            transport, endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs")
        ).query_user_bugs("alice")


def test_query_user_bugs_records_official_bug_without_stable_version() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api.php/v2/bugs/2537":
            return httpx.Response(
                200,
                json={
                    "bug": {
                        "id": 2537,
                        "status": "active",
                        "assignedTo": "alice",
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 2537,
                        "title": "【AI建站】Missing version",
                        "status": "active",
                        "assignedTo": "alice",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handle)

    result = provider(
        transport, endpoints=ZentaoEndpoints(userBugs="/api.php/v2/bugs")
    ).query_user_bugs("alice")

    assert result.items == ()
    assert result.item_failures[0].model_dump(by_alias=True) == {
        "bugId": "2537",
        "code": "MISSING_STABLE_VERSION",
        "field": "version",
        "message": "missing stable version",
    }
    assert result.coverage.complete is False


def test_query_user_bugs_retains_items_when_pagination_is_contradictory() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "bugs": [
                    {
                        "id": 2537,
                        "title": "【AI建站】Retained",
                        "status": "active",
                        "assignedTo": "alice",
                        "lastEditedDate": "2026-07-17 09:30:00",
                    }
                ],
                "page": 1,
                "pageSize": 20,
                "total": 1,
                "pages": 0,
            },
        )
    )

    result = provider(transport).query_user_bugs("alice")

    assert [item.id for item in result.items] == [2537]
    assert result.coverage.page == 1
    assert result.coverage.page_size == 20
    assert result.coverage.total == -1
    assert result.coverage.pages is None


@pytest.mark.parametrize(
    ("page", "total", "pages", "returned_ids"),
    [
        (1, 2, 1, [2537]),
        (2, 22, 2, [3397]),
    ],
)
def test_query_user_bugs_marks_underfilled_nonempty_pages_incomplete(
    page: int, total: int, pages: int, returned_ids: list[int]
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": bug_id,
                        "status": "open",
                        "version": f"v-{bug_id}",
                    }
                    for bug_id in returned_ids
                ],
                "page": page,
                "pageSize": 20,
                "total": total,
                "pages": pages,
            },
        )
    )

    result = provider(transport).query_user_bugs("alice", page=page)

    assert [item.id for item in result.items] == returned_ids
    assert result.coverage.total == -1
    assert result.coverage.pages is None


@pytest.mark.parametrize(("response_page", "response_page_size"), [(3, 20), (2, 10)])
def test_query_user_bugs_falls_back_when_response_pagination_mismatches_request(
    response_page: int, response_page_size: int
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "items": [{"id": 2537, "status": "open", "version": "v1"}],
                "page": response_page,
                "pageSize": response_page_size,
                "total": 21,
                "pages": 2,
            },
        )
    )

    result = provider(transport).query_user_bugs("alice", page=2, page_size=20)

    assert [item.id for item in result.items] == [2537]
    assert result.coverage.page == 2
    assert result.coverage.page_size == 20
    assert result.coverage.total == -1
    assert result.coverage.pages is None


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
    instance.query_user_bugs("alice")
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
    ).query_user_bugs("alice")
    assert observations == [(True, False)]


def test_password_auth_credentials_are_sent_only_to_login() -> None:
    observations: list[tuple[str, bool, bool]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        observations.append(
            (
                request.url.path,
                body.get("account") == "alice",
                body.get("password") == "password-secret",
            )
        )
        if request.url.path == "/api.php/v2/users/login":
            return httpx.Response(200, json={"token": "session-token"})
        return httpx.Response(
            200, json={"created": True, "alreadyExists": False, "commentId": "9"}
        )

    auth = ZentaoAuth(username="alice", password=SecretStr("password-secret"))
    provider(httpx.MockTransport(handle), auth=auth).add_bug_comment(
        1, "hello", True, "stable-key"
    )
    assert observations == [
        ("/api.php/v2/users/login", True, True),
        ("/api/bugs/1/comments", False, False),
    ]


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
    result = provider(
        transport,
        endpoints=ZentaoEndpoints(bugHistory="/custom/bugs/{bug_id}/history"),
    ).reconcile_comment("key-1", 1, comment=text)
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

    provider(httpx.MockTransport(handle), retry_after_cap=0).query_user_bugs("alice")
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
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        endpoints=ZentaoEndpoints(bugDetail="/custom/bugs/{bug_id}"),
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

    result = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(bugHistory="/custom/bugs/{bug_id}/history"),
    ).reconcile_comment("key", 1, comment="exact")
    assert result.comment_id == "c9"


def test_password_token_auth_covers_reads_and_multipart() -> None:
    observations: list[tuple[bool, bool]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api.php/v2/users/login":
            return httpx.Response(200, json={"token": "session-token"})
        observations.append(
            (
                request.headers.get("Authorization") == "Bearer session-token",
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
    instance.query_user_bugs("alice")
    instance.update_bug_steps_with_image(1, "steps", b"image", "x.png", "image/png")
    assert observations == [(True, False), (True, False)]


def test_user_history_and_statistics_contracts() -> None:
    requested_paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
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
        if request.url.path == "/api.php/v2/products":
            return httpx.Response(
                200,
                json={
                    "products": [
                        {"id": 1, "name": "A"},
                        {"id": "2", "name": "B"},
                        {"id": "", "name": "invalid"},
                    ],
                    "Secret-Key": "discard",
                },
            )
        return httpx.Response(
            200, json={"items": [{"id": 2, "status": "open", "version": "v2"}]}
        )

    instance = provider(
        httpx.MockTransport(handle),
        endpoints=ZentaoEndpoints(bugHistory="/custom/bugs/{bug_id}/history"),
    )
    assert instance.query_user_bugs("alice").items[0].snapshot_version == "v2"
    assert instance.query_bug_history(2, page=2, page_size=5).coverage.total == 6
    stats = instance.bug_statistics()
    assert stats.values == {"validatedProducts": 2, "complete": 0}
    assert stats.raw == {}
    assert requested_paths[-1] == "/api.php/v2/products"
    assert not any(path.endswith("/statistics") for path in requested_paths)


def test_bug_statistics_catalog_failure_is_sanitized() -> None:
    secret = "do-not-render"

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api.php/v2/products"
        return httpx.Response(200, json={"products": secret})

    with pytest.raises(ContractError) as caught:
        provider(httpx.MockTransport(handle)).bug_statistics()

    assert str(caught.value) == "product_catalog: invalid response contract"
    assert secret not in str(caught.value)


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

    provider(httpx.MockTransport(handle), retry_after_cap=0.25).query_user_bugs("alice")
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


def test_password_write_uses_cached_bearer_without_password_body() -> None:
    observations: list[tuple[bool, bool]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api.php/v2/users/login":
            return httpx.Response(200, json={"token": "session-token"})
        body = json.loads(request.content)
        observations.append(
            ("Authorization" in request.headers, bool(body.get("password")))
        )
        return httpx.Response(200, json={"created": True, "alreadyExists": False})

    auth = ZentaoAuth(username="alice", password=SecretStr("synthetic-pass"))
    provider(httpx.MockTransport(handle), auth=auth).add_bug_comment(
        1, "note", True, "key"
    )
    assert observations == [(True, False)]


def test_get_retries_connection_then_succeeds_and_exhausts() -> None:
    calls = 0

    def recover(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("synthetic detail", request=request)
        return httpx.Response(200, json={"items": []})

    provider(httpx.MockTransport(recover)).query_user_bugs("alice")
    assert calls == 2

    exhausted = 0

    def fail(request: httpx.Request) -> httpx.Response:
        nonlocal exhausted
        exhausted += 1
        raise httpx.ConnectTimeout("synthetic detail", request=request)

    from zentao_ai.zentao import TransportError

    with pytest.raises(TransportError, match="query_user_bugs"):
        provider(httpx.MockTransport(fail), max_get_retries=2).query_user_bugs("alice")
    assert exhausted == 3


def test_post_remote_protocol_error_is_unknown_without_retry() -> None:
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.RemoteProtocolError("synthetic interruption")

    with pytest.raises(UnknownWriteResultError, match="outcome unknown"):
        provider(httpx.MockTransport(handle)).add_bug_comment(1, "note", True, "key")
    assert calls == 1
