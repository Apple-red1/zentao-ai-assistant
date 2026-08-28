from __future__ import annotations

from typing import Any


def render_bug_web_urls(base_url: str, ids: list[int]) -> list[dict[str, Any]]:
    """Build standard ZenTao Bug detail links without performing any request."""
    base = base_url.rstrip("/")
    return [
        {
            "resource": "bug",
            "id": item_id,
            "url": f"{base}/index.php?m=bug&f=view&bugID={item_id}",
            "source": "zentao_standard_route",
            "verified": True,
        }
        for item_id in ids
    ]
