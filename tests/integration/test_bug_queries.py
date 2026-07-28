from __future__ import annotations

from typing import Any

from zentao_ai.bugs import BugService
from zentao_ai.models import BugFilters, Settings, UserRef, ZentaoSettings


class FakeApi:
    def __init__(self) -> None:
        self.requested_pages: list[int] = []

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        **kwargs: object,
    ) -> dict[str, Any]:
        assert path == "/products/3/bugs"
        page = int((params or {}).get("pageID", 1))
        self.requested_pages.append(page)
        start = (page - 1) * 100 + 1
        return {
            "bugs": [
                {
                    "id": bug_id,
                    "title": f"Bug {bug_id}",
                    "status": "active",
                    "assignedTo": "me",
                    "severity": 1,
                    "pri": 2,
                    "product": 3,
                }
                for bug_id in range(start, start + 100)
            ],
            "pager": {"pageTotal": 4, "pageID": page},
        }


class AssigneePaginationApi:
    def __init__(self) -> None:
        self.requested_params: list[dict[str, object]] = []

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        **kwargs: object,
    ) -> dict[str, Any]:
        assert path == "/products/2/bugs"
        request_params = dict(params or {})
        self.requested_params.append(request_params)
        page_id = int(request_params.get("pageID", 1))
        assigned_to = "another-user" if page_id == 1 else "xujiangshan"
        return {
            "bugs": [
                {
                    "id": 1000 + page_id,
                    "title": f"Page {page_id}",
                    "status": "active",
                    "assignedTo": assigned_to,
                    "severity": 3,
                    "pri": 3,
                    "product": 2,
                }
            ],
            "pager": {"pageTotal": 2, "pageID": page_id},
        }


def settings() -> Settings:
    return Settings(
        version=1,
        zentao=ZentaoSettings(base_url="https://z.example", account="me"),
    )


async def test_query_reads_every_page_until_limit() -> None:
    api = FakeApi()
    service = BugService(api, settings())

    result = await service.search_bugs(BugFilters(product_id=3, max_results=250))

    assert len(result.bugs) == 250
    assert api.requested_pages == [1, 2, 3]
    assert result.truncated is True


async def test_user_query_reads_later_pages_with_page_id() -> None:
    api = AssigneePaginationApi()
    service = BugService(api, settings())
    user = UserRef(
        id="15",
        account="xujiangshan",
        real_name="徐江珊",
        kind="inside",
    )

    result = await service.query_user_bugs(
        user,
        BugFilters(product_id=2, status="active", max_results=10),
    )

    assert [bug.id for bug in result.bugs] == [1002]
    assert [params["pageID"] for params in api.requested_params] == [1, 2]
    assert all("page" not in params for params in api.requested_params)


async def test_my_query_forces_configured_account() -> None:
    api = FakeApi()
    service = BugService(api, settings())

    result = await service.query_my_bugs(
        BugFilters(product_id=3, status="unresolved", max_results=10)
    )

    assert len(result.bugs) == 10
    assert all(bug.assigned_to == "me" for bug in result.bugs)
