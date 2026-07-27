from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any, Literal, Protocol

from zentao_ai.errors import ErrorCode, ZentaoError
from zentao_ai.models import (
    TeamMember,
    TeamValidationFailure,
    TeamValidationResult,
    UserRef,
)

UserKind = Literal["inside", "outside", "all"]
QueryValue = str | int | float | bool | None


class JsonClient(Protocol):
    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, QueryValue] | None = None,
        json: Mapping[str, object] | None = None,
        write: bool = False,
    ) -> dict[str, Any]: ...


class UserDirectory:
    def __init__(
        self,
        client: JsonClient,
        *,
        ttl_seconds: float = 300.0,
        clock: Any = time.monotonic,
    ) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._cache: dict[str, tuple[float, list[UserRef]]] = {}

    async def list_users(
        self,
        kind: UserKind = "all",
        *,
        force_refresh: bool = False,
    ) -> list[UserRef]:
        if kind == "all":
            inside = await self.list_users("inside", force_refresh=force_refresh)
            outside = await self.list_users("outside", force_refresh=force_refresh)
            return inside + outside
        if kind not in {"inside", "outside"}:
            raise ZentaoError(
                ErrorCode.VALIDATION_ERROR,
                "User kind must be inside, outside, or all.",
            )

        cached = self._cache.get(kind)
        if (
            not force_refresh
            and cached is not None
            and self._clock() - cached[0] < self._ttl_seconds
        ):
            return list(cached[1])

        users = await self._fetch_kind(kind)
        self._cache[kind] = (self._clock(), users)
        return list(users)

    async def resolve(
        self,
        query: str,
        kind: UserKind = "all",
        *,
        force_refresh: bool = False,
    ) -> UserRef:
        await self.list_users(kind, force_refresh=force_refresh)
        return self.resolve_cached(query, kind)

    def resolve_cached(self, query: str, kind: UserKind = "all") -> UserRef:
        needle = query.strip()
        if not needle:
            raise ZentaoError(ErrorCode.USER_NOT_FOUND, "User query is empty.")
        users = self._cached_for_kind(kind)

        exact_account = [user for user in users if user.account == needle]
        if exact_account:
            return self._one_or_ambiguous(needle, exact_account)

        exact_name = [user for user in users if user.real_name == needle]
        if exact_name:
            return self._one_or_ambiguous(needle, exact_name)

        folded = needle.casefold()
        folded_accounts = [user for user in users if user.account.casefold() == folded]
        if folded_accounts:
            return self._one_or_ambiguous(needle, folded_accounts)

        raise ZentaoError(
            ErrorCode.USER_NOT_FOUND,
            f"No ZenTao user matched {needle!r}.",
        )

    async def validate_team(self, members: list[TeamMember]) -> TeamValidationResult:
        resolved: list[UserRef] = []
        failures: list[TeamValidationFailure] = []
        for member in members:
            try:
                user = await self.resolve(member.account, kind="inside")
                if member.name and user.real_name and member.name != user.real_name:
                    raise ZentaoError(
                        ErrorCode.VALIDATION_ERROR,
                        "Configured name and account refer to different users.",
                    )
                resolved.append(user)
            except ZentaoError as exc:
                failures.append(
                    TeamValidationFailure(
                        name=member.name,
                        account=member.account,
                        code=exc.code.value,
                        reason=exc.message,
                    )
                )
        return TeamValidationResult(resolved=resolved, failures=failures)

    async def _fetch_kind(self, kind: Literal["inside", "outside"]) -> list[UserRef]:
        page = 1
        users: list[UserRef] = []
        while True:
            payload = await self._client.request_json(
                "GET",
                "/users",
                params={
                    "browseType": kind,
                    "page": page,
                    "recPerPage": 1000,
                },
            )
            page_items = self._extract_users(payload, kind)
            users.extend(page_items)
            total_pages = self._page_total(payload)
            if (total_pages is not None and page >= total_pages) or (
                total_pages is None and len(page_items) < 1000
            ):
                break
            page += 1
        users.sort(key=lambda user: (user.account.casefold(), user.id))
        return users

    @staticmethod
    def _extract_users(
        payload: Mapping[str, Any],
        kind: Literal["inside", "outside"],
    ) -> list[UserRef]:
        raw: Any = payload.get("users")
        if raw is None:
            raw = payload.get("data")
            if isinstance(raw, Mapping):
                raw = raw.get("users")
        if not isinstance(raw, list):
            return []

        users: list[UserRef] = []
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            account = str(item.get("account") or "").strip()
            if not account:
                continue
            deleted = item.get("deleted")
            if deleted is True or str(deleted).casefold() in {"1", "true", "yes"}:
                continue
            real_name = str(
                item.get("realname")
                or item.get("realName")
                or item.get("name")
                or ""
            ).strip()
            users.append(
                UserRef(
                    id=str(item.get("id") or account),
                    account=account,
                    real_name=real_name,
                    kind=kind,
                )
            )
        return users

    @staticmethod
    def _page_total(payload: Mapping[str, Any]) -> int | None:
        pager = payload.get("pager")
        if isinstance(pager, Mapping):
            value = pager.get("pageTotal") or pager.get("totalPage")
        else:
            value = payload.get("pageTotal")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _cached_for_kind(self, kind: UserKind) -> list[UserRef]:
        if kind == "all":
            return [
                *self._cache.get("inside", (0.0, []))[1],
                *self._cache.get("outside", (0.0, []))[1],
            ]
        if kind not in {"inside", "outside"}:
            raise ZentaoError(ErrorCode.VALIDATION_ERROR, "Invalid user kind.")
        return list(self._cache.get(kind, (0.0, []))[1])

    @staticmethod
    def _one_or_ambiguous(query: str, candidates: list[UserRef]) -> UserRef:
        if len(candidates) == 1:
            return candidates[0]
        raise ZentaoError(
            ErrorCode.USER_AMBIGUOUS,
            f"More than one ZenTao user matched {query!r}.",
            details={
                "candidates": [
                    {
                        "account": user.account,
                        "real_name": user.real_name,
                        "kind": user.kind,
                    }
                    for user in candidates
                ]
            },
        )
