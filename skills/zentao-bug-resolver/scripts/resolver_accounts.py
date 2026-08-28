"""Pure account evidence and readback checks for the Bug resolver."""

from __future__ import annotations

from typing import Any

from zentao.identity import resolve_user

CREATOR_ACCOUNT_KEYS = ("openedByAccount", "creatorAccount", "createdByAccount", "creator_account", "opened_by_account", "created_by_account")
CREATOR_OBJECT_KEYS = ("openedBy", "opened_by", "creator", "createdBy", "openedByUser", "creatorUser")


def _account_text(value: Any) -> str | None:
    """Accept account evidence, never stringify a name-only object or sentinel."""
    if not isinstance(value, str) or not value or value == "closed":
        return None
    return value if all(not char.isspace() and char.isprintable() for char in value) else None


def extract_creator_account(bug: dict[str, Any], *, users: list[dict[str, Any]] | None = None,
                            users_complete: bool = False) -> str | None:
    """Require consistent account evidence; verify bare openedBy in the directory.

    A string openedBy is a candidate, not a name lookup. Without a complete
    directory and an exact account match it remains unavailable.
    """
    accounts: set[str] = set()
    for key in CREATOR_ACCOUNT_KEYS:
        value = bug.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, dict):
            value = value.get("account")
        account = _account_text(value)
        if account is None:
            return None
        accounts.add(account)
    for key in CREATOR_OBJECT_KEYS:
        value = bug.get(key)
        if isinstance(value, dict):
            value = value.get("account")
            if value not in (None, ""):
                account = _account_text(value)
                if account is None:
                    return None
                accounts.add(account)
        elif value is not None and not isinstance(value, str):
            return None
        # Other bare creator aliases have no verified account contract.
    opened_by = bug.get("openedBy")
    if isinstance(opened_by, str) and opened_by:
        try:
            directory = _validated_user_directory(users, users_complete=users_complete)
        except ValueError:
            return None
        if opened_by not in directory:
            return None
        accounts.add(opened_by)
    return next(iter(accounts)) if len(accounts) == 1 else None


def resolve_human_assignee(bug: dict[str, Any], *, explicit_assignee: str | None = None,
                           users: list[dict[str, Any]] | None = None,
                           users_complete: bool = False) -> str:
    """Pure account selection from pre-view and, only if needed, complete users.

    Does not fetch data, authorize a resolve, or write to ZenTao. Explicit user
    lookup failures never fall back to the creator.
    """
    if explicit_assignee is None:
        opened_by = bug.get("openedBy")
        if isinstance(opened_by, str) and opened_by:
            directory = _validated_user_directory(users, users_complete=users_complete)
            if opened_by not in directory:
                raise ValueError("创建人 openedBy 在用户目录中没有区分大小写的 account 精确匹配；停止 resolve")
        account = extract_creator_account(bug, users=users, users_complete=users_complete)
        if account is None:
            raise ValueError("创建人 account 缺失、冲突或结构异常；停止 resolve")
        return account
    if not isinstance(explicit_assignee, str) or not explicit_assignee.strip():
        raise ValueError("显式负责人为空；不回退创建人")
    directory = _validated_user_directory(users, users_complete=users_complete)
    return resolve_user(directory.values(), explicit_assignee)["account"]


def _validated_user_directory(users: list[dict[str, Any]] | None, *, users_complete: bool) -> dict[str, dict[str, Any]]:
    """Keep exact duplicate rows, conflicting identities and incomplete data distinct."""
    if users_complete is not True or not isinstance(users, list):
        raise ValueError("用户列表不完整；无法验证目标账号，停止 resolve")
    by_account: dict[str, dict[str, Any]] = {}
    by_id: dict[str, str] = {}
    for row in users:
        account = _account_text(row.get("account")) if isinstance(row, dict) else None
        if account is None:
            raise ValueError("用户 account 缺失或结构异常；停止 resolve")
        if any(row.get(key) is not None and not isinstance(row[key], str) for key in ("realname", "name")):
            raise ValueError("用户姓名结构异常；停止 resolve")
        if account in by_account and row != by_account[account]:
            raise ValueError("同一用户 account 存在冲突记录；停止 resolve")
        ident = row.get("id")
        if ident not in (None, ""):
            if isinstance(ident, bool) or not isinstance(ident, (int, str)):
                raise ValueError("用户 ID 结构异常；停止 resolve")
            if str(ident) in by_id and by_id[str(ident)] != account:
                raise ValueError("同一用户 ID 对应多个 account；停止 resolve")
            by_id[str(ident)] = account
        by_account[account] = row
    return by_account


def human_readback_matches(bug: dict[str, Any], target_account: str) -> bool:
    """Check domain state/account only; the Agent must first validate Bug ID."""
    assigned = bug.get("assignedTo")
    if isinstance(assigned, dict):
        assigned = assigned.get("account")
    return (bug.get("status") == "resolved" and _account_text(target_account) is not None
            and _account_text(assigned) == target_account)
