"""Independent official-contract oracle.

This module deliberately loads only the checked-in evidence snapshot.  It
never imports ``support.CATALOG`` or derives expected values from the runtime
catalog, so a catalog mutation cannot update the oracle at test time.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


_SNAPSHOT = Path(__file__).resolve().parents[2] / "references" / "api-v2" / "official-contract.json"
OFFICIAL_SNAPSHOT: dict[str, Any] = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
OFFICIAL_ENDPOINTS: dict[str, dict[str, Any]] = {
    item["endpoint_id"]: item for item in OFFICIAL_SNAPSHOT["endpoints"]
}


def _parameter_projection(param: dict[str, Any]) -> dict[str, Any]:
    """Project a runtime parameter onto fields frozen by official evidence."""
    result = {
        key: param[key]
        for key in ("api_name", "type", "required", "repeatable")
        if key in param
    }
    if param.get("enum_map"):
        result["enum_values"] = sorted(set(param["enum_map"].values()))
    for key in ("domain", "minimum", "allowed_special_values"):
        if key in param:
            result[key] = param[key]
    return result


def _catalog_projection(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": item["method"],
        "path": item["path"],
        "official_doc": item["official_doc"],
        "parameters": {
            location: [_parameter_projection(param) for param in item["parameters"][location]]
            for location in ("path", "query", "body", "form")
        },
    }


def assert_catalog_matches_official(item: dict[str, Any]) -> None:
    """Raise an assertion with a stable field path when evidence drifts."""
    endpoint_id = item["endpoint_id"]
    expected = OFFICIAL_ENDPOINTS.get(endpoint_id)
    if expected is None:
        raise AssertionError(f"official evidence missing endpoint {endpoint_id}")
    actual = _catalog_projection(item)
    expected_projection = {
        "method": expected["method"],
        "path": expected["path"],
        "official_doc": expected["official_doc"],
        "parameters": expected["parameters"],
    }
    if actual != expected_projection:
        raise AssertionError(
            f"{endpoint_id} differs from official evidence: "
            f"expected={expected_projection!r} actual={actual!r}"
        )


def mutation(item: dict[str, Any], location: str, api_name: str) -> dict[str, Any]:
    """Return an isolated catalog copy for mutation-style oracle tests."""
    result = copy.deepcopy(item)
    return next(param for param in result["parameters"][location] if param["api_name"] == api_name)


def official_entry_count() -> int:
    return int(OFFICIAL_SNAPSHOT["endpoint_count"])


def specific_source_count() -> int:
    return sum(item.get("source_status") == "specific" for item in OFFICIAL_ENDPOINTS.values())
