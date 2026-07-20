from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

import pytest

from zentao_ai.cli.runtime import DependencyFactory


pytestmark = pytest.mark.skipif(
    os.environ.get("ZENTAO_PRODUCTION_CONTRACT_TEST") != "1",
    reason="set ZENTAO_PRODUCTION_CONTRACT_TEST=1 to run the read-only production check",
)


T = TypeVar("T")
_COLLECTION_NAMES = ("bugs", "items", "actions", "pager")


@dataclass(frozen=True)
class OperationEvidence:
    exception_class: str | None
    status_category: str
    top_level_keys: tuple[str, ...]
    collection_types: tuple[tuple[str, str], ...]


def _response_evidence(response: Any) -> OperationEvidence:
    status_category = f"{response.status_code // 100}xx"
    try:
        data = response.json()
    except ValueError:
        return OperationEvidence(
            None,
            status_category,
            (),
            tuple((name, "NoneType") for name in _COLLECTION_NAMES),
        )
    if not isinstance(data, dict):
        return OperationEvidence(
            None,
            status_category,
            (),
            tuple((name, "NoneType") for name in _COLLECTION_NAMES),
        )
    return OperationEvidence(
        None,
        status_category,
        tuple(sorted(str(name) for name in data)),
        tuple((name, type(data.get(name)).__name__) for name in _COLLECTION_NAMES),
    )


def _capture_operation(
    provider: Any, operation: Callable[[], T]
) -> tuple[T | None, OperationEvidence]:
    observed: list[OperationEvidence] = []
    request = provider._client.request

    def capture(*args: Any, **kwargs: Any) -> Any:
        response = request(*args, **kwargs)
        observed.append(_response_evidence(response))
        return response

    provider._client.request = capture
    try:
        return operation(), observed[-1]
    except Exception as error:
        evidence = observed[-1] if observed else OperationEvidence(
            None,
            "not_requested",
            (),
            tuple((name, "NoneType") for name in _COLLECTION_NAMES),
        )
        return None, OperationEvidence(
            type(error).__name__,
            evidence.status_category,
            evidence.top_level_keys,
            evidence.collection_types,
        )
    finally:
        provider._client.request = request


def test_production_query_contracts_for_weiwenting() -> None:
    runtime = DependencyFactory._production(Path(r"F:\每日工作"))
    try:
        bugs, bug_evidence = _capture_operation(
            runtime.provider,
            lambda: runtime.provider.query_user_bugs(
                "weiwenting", page=1, page_size=20
            ),
        )
        history, history_evidence = _capture_operation(
            runtime.provider,
            lambda: runtime.provider.query_bug_history(
                bugs.items[0].id if bugs and bugs.items else 0
            ),
        )

        evidence = {
            "query_user_bugs": bug_evidence,
            "query_bug_history": history_evidence,
        }
        checks = {
            "query_user_bugs": (
                bug_evidence.exception_class is None
                and bug_evidence.status_category == "2xx"
                and "bugs" in bug_evidence.top_level_keys
                and dict(bug_evidence.collection_types)["bugs"] in {"list", "dict"}
                and bool(bugs and bugs.items)
            ),
            "query_bug_history": (
                history_evidence.exception_class is None
                and history_evidence.status_category == "2xx"
                and history is not None
                and history.coverage.total >= 0
            ),
        }
        assert all(checks.values()), {"checks": checks, "evidence": evidence}
    finally:
        runtime.close()
