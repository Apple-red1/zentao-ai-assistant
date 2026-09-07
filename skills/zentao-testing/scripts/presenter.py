"""Human rendering for deterministic testing Bug results."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED = REPO_ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.bug_presenter import render_bug_table  # noqa: E402


def render_my_bugs(result: dict[str, Any]) -> str:
    urls = {
        item.get("id"): item["web_url"]
        for item in result.get("items", [])
        if item.get("id") is not None and isinstance(item.get("web_url"), str) and item["web_url"]
    }
    return render_bug_table(
        result.get("items", []),
        urls=urls,
        heading="## 我的未关闭 Bug",
        empty_message="没有未关闭 Bug。",
        complete=bool(result.get("complete")),
        partial_failures=result.get("partial_failures", []),
    )


__all__ = ["render_my_bugs"]
