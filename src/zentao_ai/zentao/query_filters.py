from __future__ import annotations

import re
import unicodedata
from typing import Literal

from .models import BugSnapshot


_LEADING_TAGS = re.compile(r"\A(?:【[^】]+】)+")
_TAG = re.compile(r"【([^】]+)】")
_UNCLOSED_STATUSES = frozenset(
    {
        "active",
        "open",
        "激活",
        "已激活",
        "打开",
        "已打开",
    }
)
_TITLE_SEARCH_SEPARATORS = frozenset("【】[]（）()-—_:：/")


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def normalize_title_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip().casefold()
    return "".join(
        char
        for char in normalized
        if not char.isspace() and char not in _TITLE_SEARCH_SEPARATORS
    )


def extract_title_tags(title: str) -> tuple[str, ...]:
    match = _LEADING_TAGS.match(title)
    if match is None:
        return ()
    return tuple(_normalize(tag) for tag in _TAG.findall(match.group()))


def is_unclosed_status(status: str) -> bool:
    return _normalize(status) in _UNCLOSED_STATUSES


def filter_assignee_bugs(
    items: tuple[BugSnapshot, ...],
    *,
    title_tag: str | None,
    status: Literal["all", "unclosed"],
) -> tuple[BugSnapshot, ...]:
    normalized_tag = _normalize(title_tag) if title_tag is not None else None
    return tuple(
        item
        for item in items
        if (normalized_tag is None or normalized_tag in extract_title_tags(item.title))
        and (status == "all" or is_unclosed_status(item.status))
    )


def filter_title_bugs(
    items: tuple[BugSnapshot, ...],
    *,
    title_keyword: str,
    status: Literal["all", "unclosed"],
) -> tuple[BugSnapshot, ...]:
    keyword = normalize_title_search_text(title_keyword)
    if not keyword:
        raise ValueError("title keyword is empty")
    return tuple(
        item
        for item in items
        if keyword in normalize_title_search_text(item.title)
        and (status == "all" or _normalize(item.status) != "closed")
    )
