
from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from typing import Any

from ..errors import ApiError, UsageError


# Mappings are scoped to protocol fields.  In particular, free-text fields
# such as title/description/comment and credential fields never consult this
# table, even when their value happens to look like an enum alias.
FIELD_ENUM_MAPS: dict[str, dict[str, str]] = {
    "browseType": {
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
    },
    "resolution": {
        "not-repro": "notrepro",
        "by-design": "bydesign",
        "will-not-fix": "willnotfix",
        "to-story": "tostory",
    },
    "closedReason": {
        "by-design": "bydesign",
        "will-not-do": "willnotdo",
    },
    "type": {
        "code-error": "codeerror",
        "design-defect": "designdefect",
    },
    "model": {
        "waterfall-plus": "waterfallplus",
        "agile-plus": "agileplus",
    },
}

_CURRENT_ENDPOINT: ContextVar[str | None] = ContextVar("zentao_endpoint", default=None)


def _enum_field_is_scoped(endpoint_id: str | None, field: str) -> bool:
    """Return whether this endpoint declares ``field`` as an enum field."""
    if endpoint_id is None:
        return True  # field-scoped helper calls remain useful in unit tests
    if field == "browseType":
        return ".list" in endpoint_id
    if field == "resolution":
        return endpoint_id == "bug.resolve"
    if field == "closedReason":
        return endpoint_id.endswith(".close")
    if field == "model":
        return endpoint_id in {"project.create", "project.edit"}
    if field == "type":
        return endpoint_id in {"bug.create", "bug.edit"}
    return False

SORT_TO_API = {"raw-id": "rawID", "name-col": "nameCol"}


def endpoint(endpoint_id: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            marker = _CURRENT_ENDPOINT.set(endpoint_id)
            try:
                result = fn(*args, **kwargs)
                return validate_endpoint_response(endpoint_id, result)
            finally:
                _CURRENT_ENDPOINT.reset(marker)

        setattr(wrapped, "__zentao_endpoint_id__", endpoint_id)
        return wrapped
    return decorate


def compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def require_success_field(result: object | None, *, endpoint_id: str, field: str, feature: str) -> object | None:
    """Reject a misleading success response that cannot support the next workflow step."""
    if result is None or (isinstance(result, dict) and result.get("status") == "success" and field not in result):
        raise ApiError(
            f"{endpoint_id} 返回 success 但缺少 {field}；请确认当前禅道已启用{feature}模块",
            {"endpoint": endpoint_id, "missing": field, "response": result},
        )
    return result


def require_response_body(result: object | None, *, endpoint_id: str, feature: str) -> object:
    if result is None:
        raise ApiError(
            f"{endpoint_id} 返回空响应；请确认当前禅道已启用{feature}能力",
            {"endpoint": endpoint_id, "response": None},
        )
    return result


# These are the response fields used by ZenTao's success envelopes. A raw
# object (the form returned by several 21.7.8 endpoints) remains valid; the
# field is required when the server explicitly returns ``status=success``.
_RESPONSE_FIELDS: dict[str, str] = {
    "bug": "bugs",
    "build": "builds",
    "epic": "epics",
    "execution": "executions",
    "feedback": "feedbacks",
    "product": "products",
    "product-plan": "productplans",
    "program": "programs",
    "project": "projects",
    "release": "releases",
    "requirement": "requirements",
    "story": "stories",
    "system": "systems",
    "task": "tasks",
    "test-case": "testcases",
    "test-task": "testtasks",
    "ticket": "tickets",
    "user": "users",
}


def _contract_field(endpoint_id: str) -> str | None:
    resource, operation = endpoint_id.split(".", 1)
    if operation == "create":
        return "id"
    if operation == "view":
        return resource.replace("-", "")
    if operation.startswith("list"):
        return _RESPONSE_FIELDS.get(resource)
    return None


def validate_endpoint_response(endpoint_id: str, result: object | None) -> object | None:
    """Validate the stable endpoint-specific part of a response contract.

    Transport-level validation (including ``status=fail`` and unexpected
    empty bodies) lives in :class:`ZentaoSession`; this function validates the
    endpoint-specific success envelope after an adapter returns. Raw objects
    are intentionally accepted because the API commonly omits the envelope.
    """
    operation = endpoint_id.split(".", 1)[1]
    if result is None:
        # DELETE adapters normalize a legal 204 to an explicit success object.
        if operation == "delete":
            return result
        raise ApiError(
            f"{endpoint_id} 返回空响应",
            {"endpoint": endpoint_id, "response": None},
        )

    field = _contract_field(endpoint_id)
    if field and isinstance(result, dict) and result.get("status") == "success" and field not in result:
        raise ApiError(
            f"{endpoint_id} 返回 success 但缺少 {field}",
            {"endpoint": endpoint_id, "missing": field, "response": result},
        )
    return result


def map_enum(field: str, value: Any) -> Any:
    if isinstance(value, list):
        return [map_enum(field, item) for item in value]
    if not isinstance(value, str):
        return value
    # The endpoint context is intentionally part of the lookup boundary. A
    # direct helper call (outside an adapter) still supports field-level unit
    # tests, but no value-only/global fallback exists anymore.
    endpoint_id = _CURRENT_ENDPOINT.get()
    if not _enum_field_is_scoped(endpoint_id, field):
        return value
    mapping = FIELD_ENUM_MAPS.get(field, {})
    if endpoint_id is None:
        return mapping.get(value, value)
    return mapping.get(value, value)


def make_order_by(sort: str, order: str | None) -> str:
    api_sort = SORT_TO_API.get(sort, sort.replace("-", "_"))
    return f"{api_sort}_{order or 'asc'}"


def validate_pagination(page: object | None, per_page: object | None) -> None:
    if page is not None and (not isinstance(page, int) or page < 1):
        raise UsageError("--page 必须大于等于 1")
    if per_page is not None and (not isinstance(per_page, int) or not 1 <= per_page <= 1000):
        raise UsageError("--per-page 必须在 1 到 1000 之间")
