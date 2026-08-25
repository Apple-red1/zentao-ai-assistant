
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..errors import UsageError


ENUM_TO_API = {
    "assigned-to-me": "assignedtome",
    "opened-by-me": "openedbyme",
    "assigned-by-me": "assignedbyme",
    "resolved-by-me": "resolvedbyme",
    "postponed-by-me": "postponedbyme",
    "review-by-me": "reviewbyme",
    "draft-story": "draftstory",
    "all-story": "allstory",
    "my-involved": "myinvolved",
    "need-confirm": "needconfirm",
    "to-closed": "toclosed",
    "long-life-bugs": "longlifebugs",
    "finished-by-me": "finishedbyme",
    "assign-to-me": "assigntome",
    "not-repro": "notrepro",
    "by-design": "bydesign",
    "will-not-fix": "willnotfix",
    "to-story": "tostory",
    "will-not-do": "willnotdo",
    "code-error": "codeerror",
    "design-defect": "designdefect",
    "waterfall-plus": "waterfallplus",
    "agile-plus": "agileplus",
}

SORT_TO_API = {"raw-id": "rawID", "name-col": "nameCol"}


def endpoint(endpoint_id: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, "__zentao_endpoint_id__", endpoint_id)
        return fn
    return decorate


def compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def map_enum(field: str, value: Any) -> Any:
    if isinstance(value, list):
        return [map_enum(field, item) for item in value]
    if not isinstance(value, str):
        return value
    return ENUM_TO_API.get(value, value)


def make_order_by(sort: str, order: str | None) -> str:
    api_sort = SORT_TO_API.get(sort, sort.replace("-", "_"))
    return f"{api_sort}_{order or 'asc'}"


def validate_pagination(page: object | None, per_page: object | None) -> None:
    if page is not None and (not isinstance(page, int) or page < 1):
        raise UsageError("--page 必须大于等于 1")
    if per_page is not None and (not isinstance(per_page, int) or not 1 <= per_page <= 1000):
        raise UsageError("--per-page 必须在 1 到 1000 之间")
