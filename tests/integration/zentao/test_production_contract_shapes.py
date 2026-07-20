from __future__ import annotations

import os
from pathlib import Path

import pytest

from zentao_ai.cli.runtime import DependencyFactory


pytestmark = pytest.mark.skipif(
    os.environ.get("ZENTAO_PRODUCTION_CONTRACT_TEST") != "1",
    reason="set ZENTAO_PRODUCTION_CONTRACT_TEST=1 to run the read-only production check",
)


def test_production_query_contracts_for_weiwenting() -> None:
    runtime = DependencyFactory._production(Path(r"F:\每日工作"))
    try:
        bugs = runtime.provider.query_user_bugs("weiwenting", page=1, page_size=20)

        assert bugs.items

        history = runtime.provider.query_bug_history(bugs.items[0].id)

        assert history.coverage.total >= 0
    finally:
        runtime.close()
