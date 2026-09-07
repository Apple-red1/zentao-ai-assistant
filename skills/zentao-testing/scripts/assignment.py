"""Pure, auditable owner selection for testing Bug creation."""
from __future__ import annotations

from typing import Any


class AssignmentError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def decide_assignment(*, frontend_account: str | None, backend_account: str | None,
                      explicit_assignee: str | None = None, explicit_side: str | None = None,
                      evidence_side: str | None = None) -> dict[str, Any]:
    """Apply explicit assignee > explicit side > evidence > backend fallback."""
    for name, value in (("frontend_account", frontend_account), ("backend_account", backend_account)):
        if not isinstance(value, str) or not value or value != value.strip():
            raise AssignmentError("OWNER_MISSING", f"{name} 未配置真实 account")
    if explicit_assignee is not None:
        if not isinstance(explicit_assignee, str) or not explicit_assignee or explicit_assignee != explicit_assignee.strip():
            raise AssignmentError("ASSIGNEE_INVALID", "显式负责人无效")
        return {"side": "explicit", "assignee": explicit_assignee, "assignment_source": "explicit_assignee"}
    if explicit_side not in (None, "frontend", "backend") or evidence_side not in (None, "frontend", "backend"):
        raise AssignmentError("SIDE_INVALID", "前后端选择无效")
    side = explicit_side or evidence_side or "backend"
    source = ("explicit_frontend" if explicit_side == "frontend" else
              "explicit_backend" if explicit_side == "backend" else
              "evidence_frontend" if evidence_side == "frontend" else
              "evidence_backend" if evidence_side == "backend" else "default_backend")
    return {"side": side, "assignee": frontend_account if side == "frontend" else backend_account,
            "assignment_source": source}


__all__ = ["AssignmentError", "decide_assignment"]
