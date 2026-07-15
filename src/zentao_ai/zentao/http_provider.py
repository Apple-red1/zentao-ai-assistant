from __future__ import annotations

import base64
import hashlib
import re
import time
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

    def query_my_bugs(self, *, page: int = 1, page_size: int = 20) -> BugPage:
        return self._bug_page("query_my_bugs", self._endpoints.my_bugs, page, page_size)

    def query_user_bugs(
        self, user: str, *, page: int = 1, page_size: int = 20
    ) -> BugPage:
        return self._bug_page(
            "query_user_bugs",
            self._endpoints.user_bugs.format(user=self._segment(user)),
            page,
            page_size,
        )

    def query_bug_detail(self, bug_id: int | str) -> BugSnapshot:
        data = self._request(
            "GET",
            self._endpoints.bug_detail.format(bug_id=self._segment(bug_id)),
            "query_bug_detail",
        )
        return self._snapshot(data, "query_bug_detail")

    def query_bug_history(
        self, bug_id: int | str, *, page: int = 1, page_size: int = 20
    ) -> HistoryPage:
        data = self._request(
            "GET",
            self._endpoints.bug_history.format(bug_id=self._segment(bug_id)),
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
        data = self._request("GET", self._endpoints.statistics, "bug_statistics")
        source = data.get("values", data.get("statistics", data))
        if not isinstance(source, Mapping) or any(
            not isinstance(v, int) for v in source.values()
        ):
            raise ContractError("bug_statistics: invalid response contract")
        return BugStatistics(values=dict(source), raw=self._sanitize(data))

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
        if mode == "password" and not write and self._auth.password is not None:
            username = self._auth.username or ""
            token = base64.b64encode(
                f"{username}:{self._auth.password.get_secret_value()}".encode()
            ).decode("ascii")
            result["Authorization"] = f"Basic {token}"
        elif mode == "token" and self._auth.api_token is not None:
            result["Authorization"] = (
                f"Bearer {self._auth.api_token.get_secret_value()}"
            )
        elif mode == "cookie" and self._auth.web_cookie is not None:
            result["Cookie"] = self._auth.web_cookie.get_secret_value()
        return result

    def _request(
        self,
        method: str,
        path: str,
        operation: str,
        *,
        write: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        mode = self._auth_mode()
        kwargs["headers"] = {**self._headers(write=write), **kwargs.get("headers", {})}
        if (
            write
            and mode == "password"
            and self._auth.password is not None
            and "json" in kwargs
        ):
            kwargs["json"] = {
                **kwargs["json"],
                "account": self._auth.username,
                "password": self._auth.password.get_secret_value(),
            }
        if (
            write
            and mode == "password"
            and self._auth.password is not None
            and "data" in kwargs
        ):
            kwargs["data"] = {
                **kwargs["data"],
                "account": self._auth.username or "",
                "password": self._auth.password.get_secret_value(),
            }
        attempts = 1 if method != "GET" else self._max_get_retries + 1
        for attempt in range(attempts):
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
                    continue
                raise TransportError(f"{operation}: transport failure") from None
            if (
                method == "GET"
                and response.status_code in (502, 503, 504)
                and attempt + 1 < attempts
            ):
                self._sleep_retry_after(response.headers.get("Retry-After"))
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
        self, operation: str, path: str, page: int, page_size: int
    ) -> BugPage:
        data = self._request(
            "GET", path, operation, params={"page": page, "pageSize": page_size}
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
