from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from collections.abc import Mapping
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import httpx

from .errors import (
    AuthenticationError,
    ContractError,
    PermissionDeniedError,
    TransportError,
    UnknownWriteResultError,
)
from .models import (
    BugHistoryEntry,
    BugPage,
    BugSnapshot,
    BugStatistics,
    CommentWriteResult,
    Coverage,
    HistoryPage,
    StepUpdateResult,
    ZentaoAuth,
    ZentaoEndpoints,
)


class HttpZentaoProvider:
    _CATALOG_PAGE_SIZE = 100
    _MAX_CATALOG_PAGES = 100
    _MAX_BUG_PAGES_PER_PRODUCT = 100
    _MAX_USER_BUG_PAGES = 100

    def __init__(
        self,
        *,
        base_url: str,
        endpoints: ZentaoEndpoints,
        auth: ZentaoAuth | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: httpx.Timeout | None = None,
        max_get_retries: int = 2,
        retry_after_cap: float = 2.0,
    ) -> None:
        self._auth = auth or ZentaoAuth(apiToken=None, webCookie=None)
        self._endpoints = endpoints
        self._max_get_retries = max(0, max_get_retries)
        self._retry_after_cap = max(0.0, retry_after_cap)
        self._password_token: str | None = None
        self._client = httpx.Client(
            base_url=base_url,
            transport=transport,
            timeout=timeout or httpx.Timeout(connect=5, read=15, write=15, pool=5),
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(base_url={self._client.base_url!s})"

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpZentaoProvider:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def query_my_bugs(
        self, *, scope_names: tuple[str, ...] = (), page: int = 1, page_size: int = 20
    ) -> BugPage:
        if (
            isinstance(page, bool)
            or not isinstance(page, int)
            or page < 1
            or isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 1000
        ):
            raise ValueError("invalid pagination")
        requested_page = page
        requested_page_size = page_size
        catalog, catalog_complete = self._load_complete_product_catalog()
        products, incomplete = self._resolve_products(catalog, scope_names)
        incomplete = incomplete or not catalog_complete
        if not catalog_complete:
            products = ()
        snapshots: list[BugSnapshot] = []
        seen_ids: set[str] = set()
        start = (requested_page - 1) * requested_page_size
        end = start + requested_page_size
        all_products_complete = True
        for product_index, product_id in enumerate(products):
            product_complete, metadata_trustworthy = self._read_product_bugs(
                product_id,
                requested_page_size,
                snapshots,
                seen_ids,
                stop_after=end,
            )
            if not product_complete or not metadata_trustworthy:
                incomplete = True
            if not product_complete:
                all_products_complete = False
                break
            if len(snapshots) >= end and product_index + 1 < len(products):
                all_products_complete = False
                break
        complete = not incomplete and all_products_complete
        total = len(snapshots) if complete else -1
        return BugPage(
            items=tuple(snapshots[start:end]),
            coverage=Coverage(
                page=requested_page,
                pageSize=requested_page_size,
                total=total,
                pages=(total + requested_page_size - 1) // requested_page_size
                if complete
                else None,
            ),
        )

    def _load_complete_product_catalog(
        self,
    ) -> tuple[tuple[tuple[str, str], ...], bool]:
        catalog: list[tuple[str, str]] = []
        seen_pages: set[tuple[tuple[str, str], ...]] = set()
        fetched = 0
        expected_total: int | None = None
        expected_pages: int | None = None
        metadata_trustworthy = True
        invalid_metadata_seen = False
        for page in range(1, self._MAX_CATALOG_PAGES + 1):
            products, raw_count, total, pages, metadata_invalid = (
                self._load_product_catalog_page(
                    page=page, page_size=self._CATALOG_PAGE_SIZE
                )
            )
            invalid_metadata_seen = invalid_metadata_seen or metadata_invalid
            if raw_count == 0:
                if invalid_metadata_seen:
                    return tuple(catalog), False
                if not metadata_trustworthy and (
                    expected_total is not None or expected_pages is not None
                ):
                    return tuple(catalog), False
                if expected_total is not None and fetched < expected_total:
                    return tuple(catalog), False
                if expected_pages is not None and page < expected_pages:
                    return tuple(catalog), False
                return tuple(catalog), True
            if products in seen_pages:
                return tuple(catalog), False
            seen_pages.add(products)
            catalog.extend(products)
            fetched += raw_count
            if total is None or pages is None:
                metadata_trustworthy = False
            elif expected_total is None and expected_pages is None:
                expected_total, expected_pages = total, pages
            elif total != expected_total or pages != expected_pages:
                metadata_trustworthy = False
            if (
                metadata_trustworthy
                and expected_total is not None
                and expected_pages is not None
                and fetched == expected_total
                and page >= expected_pages
            ):
                return tuple(catalog), True
            if expected_total is not None and fetched > expected_total:
                metadata_trustworthy = False
        return tuple(catalog), False

    def _read_product_bugs(
        self,
        product_id: str,
        page_size: int,
        snapshots: list[BugSnapshot],
        seen_ids: set[str],
        *,
        stop_after: int,
    ) -> tuple[bool, bool]:
        seen_pages: set[tuple[str, ...]] = set()
        fetched = 0
        expected_total: int | None = None
        expected_pages: int | None = None
        metadata_trustworthy = True
        invalid_metadata_seen = False
        for product_page in range(1, self._MAX_BUG_PAGES_PER_PRODUCT + 1):
            data = self._request(
                "GET",
                self._endpoints.product_bugs.format(
                    product_id=self._segment(product_id)
                ),
                "query_my_bugs",
                params={
                    "browseType": "assignedtome",
                    "recPerPage": page_size,
                    "pageID": product_page,
                },
            )
            bugs = data.get("bugs")
            if not isinstance(bugs, list) or any(
                not isinstance(bug, Mapping) for bug in bugs
            ):
                raise ContractError("query_my_bugs: invalid bugs contract")
            if not bugs:
                if invalid_metadata_seen:
                    return False, False
                if not metadata_trustworthy and (
                    expected_total is not None or expected_pages is not None
                ):
                    return False, False
                if expected_total is not None and fetched < expected_total:
                    return False, False
                if expected_pages is not None and product_page < expected_pages:
                    return False, False
                return True, True
            page_ids = tuple(self._normalized_text(bug.get("id")) for bug in bugs)
            if page_ids in seen_pages:
                return False, False
            seen_pages.add(page_ids)
            total = data.get("total")
            invalid_metadata_seen = invalid_metadata_seen or (
                "total" in data
                and (isinstance(total, bool) or not isinstance(total, int) or total < 0)
            )
            if isinstance(total, bool) or not isinstance(total, int) or total < 0:
                metadata_trustworthy = False
            elif expected_total is None:
                expected_total = total
            elif total != expected_total:
                metadata_trustworthy = False
            pages = data.get("pages")
            invalid_metadata_seen = invalid_metadata_seen or (
                "pages" in data
                and (isinstance(pages, bool) or not isinstance(pages, int) or pages < 0)
            )
            if pages is None:
                metadata_trustworthy = False
            elif (
                isinstance(pages, bool)
                or not isinstance(pages, int)
                or pages < 0
                or (
                    expected_total is not None
                    and pages != (expected_total + page_size - 1) // page_size
                )
            ):
                metadata_trustworthy = False
            elif expected_pages is None:
                expected_pages = pages
            elif pages != expected_pages:
                metadata_trustworthy = False
            fetched += len(bugs)
            for bug in bugs:
                snapshot = self._official_snapshot(bug)
                normalized_id = self._normalized_text(snapshot.id)
                if normalized_id in seen_ids:
                    continue
                seen_ids.add(normalized_id)
                snapshots.append(snapshot)
            if expected_total is not None and fetched > expected_total:
                metadata_trustworthy = False
            if (
                metadata_trustworthy
                and expected_total is not None
                and expected_pages is not None
                and fetched == expected_total
                and product_page >= expected_pages
            ):
                return True, metadata_trustworthy
            if len(snapshots) >= stop_after:
                return False, metadata_trustworthy
        return False, False

    @classmethod
    def _resolve_products(
        cls,
        catalog: tuple[tuple[str, str], ...],
        scope_names: tuple[str, ...],
    ) -> tuple[tuple[str, ...], bool]:
        by_name: dict[str, list[str]] = {}
        for product_id, name in catalog:
            ids = by_name.setdefault(cls._normalized_text(name), [])
            if product_id not in ids:
                ids.append(product_id)
        resolved: list[str] = []
        seen: set[str] = set()
        incomplete = False
        for scope_name in scope_names:
            matches = by_name.get(cls._normalized_text(scope_name), [])
            if len(matches) != 1:
                incomplete = True
                continue
            product_id = matches[0]
            if product_id not in seen:
                seen.add(product_id)
                resolved.append(product_id)
        return tuple(resolved), incomplete

    @staticmethod
    def _normalized_text(value: object) -> str:
        return unicodedata.normalize("NFKC", str(value).strip()).casefold()

    @classmethod
    def _account(cls, value: Any) -> str | None:
        if isinstance(value, Mapping):
            value = value.get("account")
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            return None
        account = str(value).strip()
        return account or None

    @classmethod
    def _official_snapshot(
        cls, data: Mapping[str, Any], operation: str = "query_my_bugs"
    ) -> BugSnapshot:
        last_edited = data.get("lastEditedDate")
        version = (
            last_edited
            if isinstance(last_edited, (str, int)) and str(last_edited).strip()
            else data.get("version")
        )
        if (
            isinstance(version, bool)
            or not isinstance(version, (str, int))
            or not str(version).strip()
        ):
            raise ContractError(f"{operation}: missing stable version")
        normalized = {
            "id": data.get("id"),
            "status": data.get("status"),
            "title": data.get("title", ""),
            "steps": data.get("steps", ""),
            "creator": cls._account(data.get("openedBy")),
            "assignee": cls._account(data.get("assignedTo")),
            "version": str(version).strip(),
            "snapshotVersion": str(version).strip(),
            "raw": cls._sanitize(data),
        }
        try:
            return BugSnapshot.model_validate(normalized)
        except Exception:
            raise ContractError(f"{operation}: invalid bug contract") from None

    def _load_product_catalog(
        self, *, page: int = 1, page_size: int = 100
    ) -> tuple[tuple[str, str], ...]:
        products, _, _, _, _ = self._load_product_catalog_page(
            page=page, page_size=page_size
        )
        return products

    def _load_product_catalog_page(
        self, *, page: int, page_size: int
    ) -> tuple[tuple[tuple[str, str], ...], int, int | None, int | None, bool]:
        data = self._request(
            "GET",
            self._endpoints.products,
            "product_catalog",
            params={
                "browseType": "all",
                "recPerPage": min(max(page_size, 1), 100),
                "pageID": max(page, 1),
            },
        )
        products = data.get("products")
        if not isinstance(products, list):
            raise ContractError("product_catalog: invalid response contract")
        result: list[tuple[str, str]] = []
        for product in products:
            if not isinstance(product, Mapping):
                continue
            product_id = self._catalog_text(product.get("id"))
            name = self._catalog_text(product.get("name"))
            if product_id is not None and name is not None:
                result.append((product_id, name))
        total = data.get("total")
        pages = data.get("pages")
        valid_total = (
            total
            if isinstance(total, int) and not isinstance(total, bool) and total >= 0
            else None
        )
        valid_pages = (
            pages
            if isinstance(pages, int) and not isinstance(pages, bool) and pages >= 0
            else None
        )
        metadata_invalid = ("total" in data and valid_total is None) or (
            "pages" in data and valid_pages is None
        )
        return tuple(result), len(products), valid_total, valid_pages, metadata_invalid

    @staticmethod
    def _catalog_text(value: Any) -> str | None:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            return None
        normalized = str(value).strip()
        return normalized or None

    def query_user_bugs(
        self,
        user: str,
        *,
        scope_names: tuple[str, ...] = (),
        page: int = 1,
        page_size: int = 20,
    ) -> BugPage:
        operation = "query_user_bugs"
        configured_official = self._endpoints.user_bugs == "/api.php/v2/bugs"
        if configured_official:
            return self._query_official_user_bugs(
                user,
                scope_names=scope_names,
                page=page,
                page_size=page_size,
            )
        path = self._endpoints.user_bugs
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if scope_names:
            params["scopeNames"] = list(scope_names)
        data = self._request(
            "GET",
            path.format(user=self._segment(user)),
            operation,
            params=params,
        )
        if "items" in data:
            items = tuple(
                self._snapshot(item, operation) for item in self._items(data, operation)
            )
        elif "bugs" in data:
            bugs = data.get("bugs")
            if isinstance(bugs, Mapping):
                bugs = [
                    value for _, value in sorted(bugs.items(), key=lambda x: str(x[0]))
                ]
            if not isinstance(bugs, list) or any(
                not isinstance(item, Mapping) for item in bugs
            ):
                raise ContractError(f"{operation}: invalid items")
            items = tuple(
                self._official_snapshot(item, operation=operation) for item in bugs
            )
        else:
            raise ContractError(f"{operation}: invalid items")
        pager = data.get("pager")
        coverage_data = data
        if isinstance(pager, Mapping):
            coverage_data = {
                **data,
                "page": pager.get("pageID"),
                "pageSize": pager.get("recPerPage"),
                "total": pager.get("recTotal"),
                "pages": pager.get("pageTotal"),
            }
        return BugPage(
            items=items,
            coverage=self._safe_query_coverage(
                coverage_data, page, page_size, len(items)
            ),
        )

    def _query_official_user_bugs(
        self,
        user: str,
        *,
        scope_names: tuple[str, ...],
        page: int,
        page_size: int,
    ) -> BugPage:
        self._validate_pagination(page, page_size)
        operation = "query_user_bugs"
        requested_account = self._normalized_text(user)
        snapshots: list[BugSnapshot] = []
        seen_ids: set[str] = set()
        upstream_seen_ids: set[str] = set()
        seen_pages: set[tuple[str | None, ...]] = set()
        expected_total: int | None = None
        expected_pages: int | None = None
        fetched = 0
        complete = False

        for upstream_page in range(1, self._MAX_USER_BUG_PAGES + 1):
            params: dict[str, Any] = {"page": upstream_page, "limit": page_size}
            if scope_names:
                params["scopeNames"] = list(scope_names)
            data = self._request(
                "GET",
                self._endpoints.user_bugs,
                operation,
                params=params,
            )
            bugs = self._official_bug_rows(data, operation)
            page_ids = tuple(self._normalized_bug_id(item.get("id")) for item in bugs)
            repeated = page_ids in seen_pages
            seen_pages.add(page_ids)
            overlaps_prior_page = any(
                bug_id in upstream_seen_ids for bug_id in page_ids if bug_id is not None
            )
            upstream_seen_ids.update(
                bug_id for bug_id in page_ids if bug_id is not None
            )

            for item in bugs:
                assignee = self._account(item.get("assignedTo"))
                if (
                    assignee is None
                    or self._normalized_text(assignee) != requested_account
                ):
                    continue
                normalized_id = self._normalized_bug_id(item.get("id"))
                if normalized_id is None:
                    if not self._has_stable_version(item):
                        raise ContractError(f"{operation}: missing Bug id for detail")
                    raise ContractError(f"{operation}: invalid bug contract")
                if normalized_id in seen_ids:
                    continue
                seen_ids.add(normalized_id)
                snapshots.append(
                    self._official_user_snapshot(
                        item,
                        normalized_id=normalized_id,
                        requested_account=requested_account,
                    )
                )

            metadata = self._official_page_metadata(
                data,
                requested_page=upstream_page,
                requested_page_size=page_size,
                count=len(bugs),
            )
            fetched += len(bugs)
            if repeated or overlaps_prior_page:
                break
            if metadata is None:
                if expected_total is not None or expected_pages is not None or not bugs:
                    break
                continue
            total, pages = metadata
            if expected_total is None and expected_pages is None:
                expected_total, expected_pages = total, pages
            elif total != expected_total or pages != expected_pages:
                break
            if fetched > total:
                break
            if fetched == total and (
                (pages == 0 and upstream_page == 1) or upstream_page == pages
            ):
                complete = True
                break
            if upstream_page >= pages:
                break

        start = (page - 1) * page_size
        total = len(snapshots) if complete else -1
        return BugPage(
            items=tuple(snapshots[start : start + page_size]),
            coverage=Coverage(
                page=page,
                pageSize=page_size,
                total=total,
                pages=(total + page_size - 1) // page_size if complete else None,
            ),
        )

    @staticmethod
    def _official_bug_rows(
        data: Mapping[str, Any], operation: str
    ) -> list[Mapping[str, Any]]:
        bugs = data.get("bugs")
        if isinstance(bugs, Mapping):
            bugs = [
                value
                for _, value in sorted(bugs.items(), key=lambda item: str(item[0]))
            ]
        if not isinstance(bugs, list) or any(
            not isinstance(item, Mapping) for item in bugs
        ):
            raise ContractError(f"{operation}: invalid items")
        return bugs

    @staticmethod
    def _has_stable_version(data: Mapping[str, Any]) -> bool:
        for field in ("lastEditedDate", "version"):
            value = data.get(field)
            if (
                not isinstance(value, bool)
                and isinstance(value, (str, int))
                and str(value).strip()
            ):
                return True
        return False

    @classmethod
    def _normalized_bug_id(cls, value: Any) -> str | None:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            return None
        normalized = cls._normalized_text(value)
        return normalized or None

    def _official_user_snapshot(
        self,
        data: Mapping[str, Any],
        *,
        normalized_id: str,
        requested_account: str,
    ) -> BugSnapshot:
        operation = "query_user_bugs"
        if self._has_stable_version(data):
            return self._official_snapshot(data, operation=operation)
        try:
            detail = self.query_bug_detail(data["id"])
        except ContractError as error:
            if str(error) == "query_bug_detail: missing stable version":
                raise ContractError(
                    f"{operation}: detail missing stable version"
                ) from None
            raise ContractError(f"{operation}: invalid detail snapshot") from None
        if self._normalized_bug_id(detail.id) != normalized_id:
            raise ContractError(f"{operation}: detail Bug id changed")
        if (
            detail.assignee is None
            or self._normalized_text(detail.assignee) != requested_account
        ):
            raise ContractError(f"{operation}: detail assignee changed")
        return detail

    @staticmethod
    def _official_page_metadata(
        data: Mapping[str, Any],
        *,
        requested_page: int,
        requested_page_size: int,
        count: int,
    ) -> tuple[int, int] | None:
        pager = data.get("pager")
        if "pager" in data:
            if not isinstance(pager, Mapping):
                return None
            response_page = pager.get("pageID")
            response_page_size = pager.get("recPerPage")
            total = pager.get("recTotal")
            pages = pager.get("pageTotal")
        else:
            response_page = data.get("page")
            response_page_size = data.get("limit", data.get("pageSize"))
            total = data.get("total")
            pages = data.get("pages")
        if (
            isinstance(response_page, bool)
            or not isinstance(response_page, int)
            or isinstance(response_page_size, bool)
            or not isinstance(response_page_size, int)
            or isinstance(total, bool)
            or not isinstance(total, int)
        ):
            return None
        if response_page < 1 or response_page_size < 1 or total < 0:
            return None
        calculated_pages = (total + response_page_size - 1) // response_page_size
        if pages is None:
            pages = calculated_pages
        if (
            isinstance(pages, bool)
            or not isinstance(pages, int)
            or pages < 0
            or response_page != requested_page
            or response_page_size != requested_page_size
            or pages != calculated_pages
        ):
            return None
        expected_count = min(
            response_page_size,
            max(total - (response_page - 1) * response_page_size, 0),
        )
        if count != expected_count or (pages > 0 and response_page > pages):
            return None
        return total, pages

    @staticmethod
    def _safe_query_coverage(
        data: Mapping[str, Any], page: int, page_size: int, count: int
    ) -> Coverage:
        response_page = data.get("page")
        response_page_size = data.get("pageSize")
        total = data.get("total")
        pages = data.get("pages")
        valid_page = (
            isinstance(response_page, int)
            and not isinstance(response_page, bool)
            and response_page >= 1
        )
        valid_page_size = (
            isinstance(response_page_size, int)
            and not isinstance(response_page_size, bool)
            and response_page_size >= 1
        )
        valid_total: int | None = None
        if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
            valid_total = total
        valid_pages: int | None = None
        if isinstance(pages, int) and not isinstance(pages, bool) and pages >= 0:
            valid_pages = pages
        metadata_valid = (
            valid_page
            and valid_page_size
            and valid_total is not None
            and valid_pages is not None
            and response_page == page
            and response_page_size == page_size
            and valid_pages == (valid_total + page_size - 1) // page_size
            and count == min(page_size, max(valid_total - (page - 1) * page_size, 0))
            and (valid_pages == 0 or page <= valid_pages)
        )
        return Coverage(
            page=page,
            pageSize=page_size,
            total=(valid_total if metadata_valid and valid_total is not None else -1),
            pages=valid_pages if metadata_valid else None,
        )

    def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
        data = self._request(
            "GET",
            self._endpoints.bug_detail.format(bug_id=self._segment(bug_id)),
            "query_bug_detail",
        )
        if self._endpoints.bug_detail == "/api.php/v2/bugs/{bug_id}":
            bug = data.get("bug")
            if not isinstance(bug, Mapping):
                raise ContractError("query_bug_detail: invalid bug contract")
            return self._official_snapshot(bug, operation="query_bug_detail")
        return self._snapshot(data, "query_bug_detail")

    def query_bug_history(
        self, bug_id: int | str, *, page: int = 1, page_size: int = 20
    ) -> HistoryPage:
        self._validate_pagination(page, page_size)
        if self._endpoints.bug_history is None:
            raise ContractError("query_bug_history: unsupported by official contract")
        path = self._endpoints.bug_history.format(bug_id=self._segment(bug_id))
        if self._endpoints.bug_history == "/api.php/v2/bugs/{bug_id}":
            data = self._request("GET", path, "query_bug_history")
            bug = data.get("bug")
            requested_id = self._normalized_bug_id(bug_id)
            if (
                requested_id is None
                or not isinstance(bug, Mapping)
                or self._normalized_bug_id(bug.get("id")) != requested_id
            ):
                raise ContractError("query_bug_history: invalid bug contract")
            all_items = tuple(
                self._official_history(item, "query_bug_history")
                for item in self._actions(data, "query_bug_history")
            )
            start = (page - 1) * page_size
            total = len(all_items)
            return HistoryPage(
                items=all_items[start : start + page_size],
                coverage=Coverage(
                    page=page,
                    pageSize=page_size,
                    total=total,
                    pages=(total + page_size - 1) // page_size,
                ),
            )
        data = self._request(
            "GET",
            path,
            "query_bug_history",
            params={"page": page, "pageSize": page_size},
        )
        items = tuple(
            self._history(x, "query_bug_history")
            for x in self._items(data, "query_bug_history")
        )
        return HistoryPage(
            items=items, coverage=self._coverage(data, page, page_size, len(items))
        )

    def bug_statistics(self) -> BugStatistics:
        products = self._load_product_catalog(page=1, page_size=1)
        return BugStatistics(
            values={"validatedProducts": len(products), "complete": 0}, raw={}
        )

    def add_bug_comment(
        self, bug_id: int | str, comment: str, confirm: bool, idempotency_key: str
    ) -> CommentWriteResult:
        comment, key = comment.strip(), idempotency_key.strip()
        if not comment or not key or not confirm:
            raise ValueError(
                "comment and idempotencyKey must be nonempty and confirm must be true"
            )
        data = self._request(
            "POST",
            self._endpoints.add_comment.format(bug_id=self._segment(bug_id)),
            "add_bug_comment",
            json={
                "bugId": bug_id,
                "comment": comment,
                "confirm": True,
                "idempotencyKey": key,
            },
            write=True,
        )
        return self._comment_result(data, "add_bug_comment")

    def reconcile_comment(
        self, idempotency_key: str, bug_id: int | str, *, comment: str | None = None
    ) -> CommentWriteResult:
        digest = (
            hashlib.sha256(comment.strip().encode("utf-8")).hexdigest()
            if comment is not None
            else None
        )
        seen = 0
        for page_number in range(1, 101):
            page = self.query_bug_history(bug_id, page=page_number, page_size=100)
            for entry in page.items:
                seen += 1
                if seen > 10_000:
                    break
                if entry.idempotency_key != idempotency_key or (
                    digest is not None and entry.content_hash != digest
                ):
                    continue
                if entry.created is True and entry.already_exists is not True:
                    return CommentWriteResult(
                        created=True,
                        alreadyExists=False,
                        commentId=entry.id,
                        status="CREATED",
                    )
                if entry.already_exists is True and entry.created is not True:
                    return CommentWriteResult(
                        created=False,
                        alreadyExists=True,
                        commentId=entry.id,
                        status="ALREADY_EXISTS",
                    )
            pages = page.coverage.pages
            if (
                seen > 10_000
                or not page.items
                or (pages is not None and page_number >= pages)
                or (pages is None and seen >= page.coverage.total)
            ):
                break
        return CommentWriteResult(
            created=False, alreadyExists=False, commentId=None, status="UNKNOWN"
        )

    def update_bug_steps(
        self, bug_id: int | str, steps: str, confirm: bool = True
    ) -> StepUpdateResult:
        if not steps.strip() or not confirm:
            raise ValueError("complete steps are required and confirm must be true")
        data = self._request(
            "POST",
            self._endpoints.update_steps.format(bug_id=self._segment(bug_id)),
            "update_bug_steps",
            json={"bugId": bug_id, "steps": steps, "confirm": True},
            write=True,
        )
        return self._step_result(data, bug_id, "update_bug_steps")

    def update_bug_steps_with_image(
        self,
        bug_id: int | str,
        steps: str,
        image: bytes,
        filename: str,
        content_type: str,
        confirm: bool = True,
    ) -> StepUpdateResult:
        if (
            not steps.strip()
            or not image
            or not filename
            or "/" in filename
            or "\\" in filename
            or not confirm
        ):
            raise ValueError(
                "validated steps, image bytes, safe filename, and confirm are required"
            )
        data = self._request(
            "POST",
            self._endpoints.update_steps.format(bug_id=self._segment(bug_id)),
            "update_bug_steps_with_image",
            data={"bugId": str(bug_id), "steps": steps, "confirm": "true"},
            files={"image": (filename, image, content_type)},
            write=True,
        )
        return self._step_result(data, bug_id, "update_bug_steps_with_image")

    def _auth_mode(self) -> str | None:
        if self._auth.api_token is not None:
            return "token"
        if self._auth.password is not None:
            return "password"
        if self._auth.web_cookie is not None:
            return "cookie"
        return None

    def _headers(self, *, write: bool) -> dict[str, str]:
        result: dict[str, str] = {}
        mode = self._auth_mode()
        if mode == "password" and self._auth.password is not None:
            result["Authorization"] = f"Bearer {self._ensure_password_token()}"
        elif mode == "token" and self._auth.api_token is not None:
            result["Authorization"] = (
                f"Bearer {self._auth.api_token.get_secret_value()}"
            )
        elif mode == "cookie" and self._auth.web_cookie is not None:
            result["Cookie"] = self._auth.web_cookie.get_secret_value()
        return result

    @staticmethod
    def _extract_login_token(payload: Mapping[str, Any]) -> str:
        candidates: list[Any] = [payload.get("token")]
        data = payload.get("data")
        if isinstance(data, Mapping):
            candidates.append(data.get("token"))
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        raise ContractError("login: missing token")

    def _ensure_password_token(self) -> str:
        if self._password_token is None:
            assert self._auth.password is not None
            try:
                response = self._client.request(
                    "POST",
                    self._endpoints.login,
                    json={
                        "account": self._auth.username or "",
                        "password": self._auth.password.get_secret_value(),
                    },
                )
            except httpx.TransportError:
                raise TransportError("login: transport failure") from None
            payload = self._decode(response, "login")
            self._password_token = self._extract_login_token(payload)
        return self._password_token

    def _request(
        self,
        method: str,
        path: str,
        operation: str,
        *,
        write: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        supplied_headers = dict(kwargs.get("headers", {}))
        kwargs["headers"] = {**self._headers(write=write), **supplied_headers}
        attempts = 1 if method != "GET" else self._max_get_retries + 1
        reauthenticated = False
        attempt = 0
        while attempt < attempts:
            try:
                response = self._client.request(method, path, **kwargs)
            except httpx.TransportError as exc:
                if write:
                    raise UnknownWriteResultError(
                        f"{operation}: write outcome unknown"
                    ) from None
                if (
                    isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout))
                    and attempt + 1 < attempts
                ):
                    attempt += 1
                    continue
                raise TransportError(f"{operation}: transport failure") from None
            if (
                response.status_code in (401, 407)
                and self._auth_mode() == "password"
                and not reauthenticated
            ):
                self._password_token = None
                refreshed_headers = {
                    key: value
                    for key, value in supplied_headers.items()
                    if key.lower() != "authorization"
                }
                kwargs["headers"] = {
                    **refreshed_headers,
                    **self._headers(write=write),
                }
                reauthenticated = True
                continue
            if (
                method == "GET"
                and response.status_code in (502, 503, 504)
                and attempt + 1 < attempts
            ):
                self._sleep_retry_after(response.headers.get("Retry-After"))
                attempt += 1
                continue
            return self._decode(response, operation)
        raise TransportError(f"{operation}: transport failure")

    def _decode(self, response: httpx.Response, operation: str) -> dict[str, Any]:
        request_id = response.headers.get("X-Request-Id")
        suffix = f" status={response.status_code}" + (
            f" request_id={request_id}" if request_id else ""
        )
        if response.status_code in (401, 407):
            raise AuthenticationError(operation + suffix)
        if response.status_code == 403:
            raise PermissionDeniedError(operation + suffix)
        if response.status_code >= 500:
            raise TransportError(operation + suffix)
        if response.status_code >= 400:
            raise ContractError(operation + suffix)
        try:
            value = response.json()
        except (ValueError, UnicodeDecodeError):
            raise ContractError(
                f"{operation}: invalid JSON response" + suffix
            ) from None
        if not isinstance(value, dict):
            raise ContractError(f"{operation}: response must be an object" + suffix)
        return value

    def _bug_page(
        self,
        operation: str,
        path: str,
        page: int,
        page_size: int,
        scope_names: tuple[str, ...] = (),
    ) -> BugPage:
        data = self._request(
            "GET",
            path,
            operation,
            params={
                "page": page,
                "pageSize": page_size,
                "scopeNames": list(scope_names),
            },
        )
        items = tuple(
            self._snapshot(x, operation) for x in self._items(data, operation)
        )
        return BugPage(
            items=items, coverage=self._coverage(data, page, page_size, len(items))
        )

    @staticmethod
    def _items(data: Mapping[str, Any], operation: str) -> list[Mapping[str, Any]]:
        items = data.get("items", [])
        if not isinstance(items, list) or any(
            not isinstance(x, Mapping) for x in items
        ):
            raise ContractError(f"{operation}: invalid items")
        return items

    @staticmethod
    def _actions(data: Mapping[str, Any], operation: str) -> list[Mapping[str, Any]]:
        actions = data.get("actions")
        if isinstance(actions, Mapping):
            items = list(actions.values())
        elif isinstance(actions, list):
            items = actions
        else:
            raise ContractError(f"{operation}: invalid actions")
        if any(not isinstance(item, Mapping) for item in items):
            raise ContractError(f"{operation}: invalid actions")
        return items

    @staticmethod
    def _validate_pagination(page: int, page_size: int) -> None:
        if (
            isinstance(page, bool)
            or not isinstance(page, int)
            or page < 1
            or isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 1000
        ):
            raise ValueError("invalid pagination")

    @classmethod
    def _snapshot(cls, data: Mapping[str, Any], operation: str) -> BugSnapshot:
        version = data.get("version")
        if version is None or not str(version).strip():
            raise ContractError(f"{operation}: missing stable version")
        safe = cls._sanitize(data)
        normalized = {
            **data,
            "version": str(version).strip(),
            "snapshotVersion": str(version).strip(),
            "raw": safe,
        }
        try:
            return BugSnapshot.model_validate(normalized)
        except Exception:
            raise ContractError(f"{operation}: invalid bug contract") from None

    @classmethod
    def _history(cls, data: Mapping[str, Any], operation: str) -> BugHistoryEntry:
        try:
            return BugHistoryEntry(**data, raw=cls._sanitize(data))
        except Exception:
            raise ContractError(f"{operation}: invalid history contract") from None

    @classmethod
    def _official_history(
        cls, data: Mapping[str, Any], operation: str
    ) -> BugHistoryEntry:
        identifier = data.get("id")
        action = data.get("action")
        if (
            isinstance(identifier, bool)
            or not isinstance(identifier, (str, int))
            or not str(identifier).strip()
            or not isinstance(action, str)
            or not action.strip()
        ):
            raise ContractError(f"{operation}: invalid history contract")
        return cls._history(data, operation)

    @staticmethod
    def _coverage(
        data: Mapping[str, Any], page: int, page_size: int, count: int
    ) -> Coverage:
        return Coverage(
            page=data.get("page", page),
            pageSize=data.get("pageSize", page_size),
            total=data.get("total", count),
            pages=data.get("pages"),
        )

    @staticmethod
    def _comment_result(data: Mapping[str, Any], operation: str) -> CommentWriteResult:
        created, exists = data.get("created"), data.get("alreadyExists")
        if (
            not isinstance(created, bool)
            or not isinstance(exists, bool)
            or created == exists
        ):
            raise ContractError(f"{operation}: invalid write result")
        return CommentWriteResult(
            created=created,
            alreadyExists=exists,
            commentId=data.get("commentId"),
            status="CREATED" if created else "ALREADY_EXISTS",
        )

    @staticmethod
    def _step_result(
        data: Mapping[str, Any], bug_id: int | str, operation: str
    ) -> StepUpdateResult:
        if data.get("updated") is not True:
            raise ContractError(f"{operation}: invalid step update result")
        return StepUpdateResult(
            updated=True,
            bugId=data.get("bugId", bug_id),
            version=str(data["version"]) if data.get("version") is not None else None,
        )

    def _sleep_retry_after(self, value: str | None) -> None:
        if not value:
            return
        try:
            delay = float(value)
        except ValueError:
            try:
                delay = max(
                    0.0,
                    (
                        parsedate_to_datetime(value)
                        - parsedate_to_datetime(
                            time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
                        )
                    ).total_seconds(),
                )
            except (TypeError, ValueError):
                return
        time.sleep(min(delay, self._retry_after_cap))

    @staticmethod
    def _segment(value: int | str) -> str:
        return quote(str(value), safe="")

    @classmethod
    def _sanitize(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for key, item in value.items():
                normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
                if any(
                    word in normalized
                    for word in (
                        "password",
                        "token",
                        "authorization",
                        "cookie",
                        "secret",
                        "credential",
                    )
                ):
                    continue
                result[str(key)] = cls._sanitize(item)
            return result
        if isinstance(value, (list, tuple)):
            return [cls._sanitize(item) for item in value]
        return value
