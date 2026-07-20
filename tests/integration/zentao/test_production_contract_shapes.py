from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from zentao_ai.cli.runtime import DependencyFactory
from zentao_ai.zentao import ContractError
from zentao_ai.zentao.models import BugPage, HistoryPage
from zentao_ai.zentao.provider import ZentaoProvider


pytestmark = pytest.mark.skipif(
    os.environ.get("ZENTAO_PRODUCTION_CONTRACT_TEST") != "1",
    reason="set ZENTAO_PRODUCTION_CONTRACT_TEST=1 to run the read-only production check",
)


_COLLECTION_NAMES = ("bugs", "items", "actions", "pager")
_PUBLIC_STATUS = "not_exposed_by_public_api"


@dataclass(frozen=True)
class OperationEvidence:
    operation: str
    outcome: str
    exception_class: str | None
    status_category: str
    top_level_keys: tuple[str, ...]
    collection_types: tuple[tuple[str, str], ...]


def _page_evidence(operation: str, items: tuple[object, ...]) -> OperationEvidence:
    return OperationEvidence(
        operation,
        "executed",
        None,
        _PUBLIC_STATUS,
        ("coverage", "items"),
        tuple(
            (name, type(items).__name__ if name == "items" else "not_exposed")
            for name in _COLLECTION_NAMES
        ),
    )


def _error_evidence(operation: str, error: Exception) -> OperationEvidence:
    return OperationEvidence(
        operation,
        "executed",
        type(error).__name__,
        _PUBLIC_STATUS,
        (),
        tuple((name, "not_exposed") for name in _COLLECTION_NAMES),
    )


def _not_executed_evidence(operation: str) -> OperationEvidence:
    return OperationEvidence(
        operation,
        "not_executed/no_bug",
        None,
        "not_executed",
        (),
        tuple((name, "not_executed") for name in _COLLECTION_NAMES),
    )


def _query_user_bugs(
    provider: ZentaoProvider,
) -> tuple[BugPage | None, OperationEvidence, Exception | None]:
    try:
        page = provider.query_user_bugs("weiwenting", page=1, page_size=20)
    except Exception as error:
        return None, _error_evidence("query_user_bugs", error), error
    return page, _page_evidence("query_user_bugs", page.items), None


def _query_bug_history(
    provider: ZentaoProvider, bug_id: int | str
) -> tuple[HistoryPage | None, OperationEvidence, Exception | None]:
    try:
        page = provider.query_bug_history(bug_id)
    except Exception as error:
        return None, _error_evidence("query_bug_history", error), error
    return page, _page_evidence("query_bug_history", page.items), None


def test_production_query_contracts_for_weiwenting() -> None:
    runtime = DependencyFactory._production(Path(r"F:\每日工作"))
    try:
        bugs, bug_evidence, bug_error = _query_user_bugs(runtime.provider)
        if bugs is not None and bugs.items:
            history, history_evidence, history_error = _query_bug_history(
                runtime.provider, bugs.items[0].id
            )
        else:
            history, history_error = None, None
            history_evidence = _not_executed_evidence("query_bug_history")

        evidence = {
            "query_user_bugs": bug_evidence,
            "query_bug_history": history_evidence,
        }
        for error in (history_error, bug_error):
            if isinstance(error, ContractError):
                raise error
        for error in (history_error, bug_error):
            if error is not None:
                raise error

        assert bugs is not None and bugs.items, evidence
        assert history is not None and history.coverage.total >= 0, evidence
    finally:
        runtime.close()
