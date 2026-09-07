"""Independent testing-team configuration and effective-team resolution."""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED = REPO_ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.identity import AmbiguousMatchError, MatchNotFoundError, resolve_user  # noqa: E402
from zentao.identity_store import IdentityScopedJsonStore  # noqa: E402
from project_config import TestingProjectStore, TestingConfigError, _lookup_project  # noqa: E402


SCHEMA_VERSION = 1
MAX_CONFIG_BYTES = 1024 * 1024


class TestingTeamError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def valid_account(value: object) -> bool:
    return (isinstance(value, str) and bool(value) and value == value.strip()
            and not any(ord(char) < 32 for char in value) and value.casefold() != "closed")


def _validate_members(value: object, label: str = "团队成员") -> None:
    if (not isinstance(value, list) or any(not valid_account(account) for account in value)
            or len(set(value)) != len(value)):
        raise TestingTeamError("TESTING_TEAM_CONFIG_INVALID", f"{label}无效；未覆盖原文件")


def empty_config(identity: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "owner": dict(identity),
        "global_default": {"members": []},
        "project_overrides": {},
    }


def _validate_config(data: dict[str, Any], identity: dict[str, str]) -> None:
    if data.get("owner") != identity:
        raise TestingTeamError("TESTING_TEAM_CONFIG_INVALID", "测试团队配置归属无效；未覆盖原文件")
    global_default = data.get("global_default")
    if not isinstance(global_default, dict):
        raise TestingTeamError("TESTING_TEAM_CONFIG_INVALID", "全局默认测试团队配置无效；未覆盖原文件")
    _validate_members(global_default.get("members"), "全局默认测试团队")
    overrides = data.get("project_overrides")
    if not isinstance(overrides, dict):
        raise TestingTeamError("TESTING_TEAM_CONFIG_INVALID", "项目测试团队覆盖配置无效；未覆盖原文件")
    aliases: set[str] = set()
    for alias, override in overrides.items():
        if not isinstance(alias, str) or not alias or alias != alias.strip() or any(ord(c) < 32 for c in alias):
            raise TestingTeamError("TESTING_TEAM_CONFIG_INVALID", "项目测试团队别名无效；未覆盖原文件")
        folded = alias.casefold()
        if folded in aliases:
            raise TestingTeamError("TESTING_TEAM_CONFIG_INVALID", "项目测试团队别名大小写冲突；未覆盖原文件")
        aliases.add(folded)
        if not isinstance(override, dict) or override.get("project_alias") != alias:
            raise TestingTeamError("TESTING_TEAM_CONFIG_INVALID", "项目测试团队覆盖归属无效；未覆盖原文件")
        project_id = override.get("project_id")
        if project_id is not None and (isinstance(project_id, bool) or not isinstance(project_id, int) or project_id <= 0):
            raise TestingTeamError("TESTING_TEAM_CONFIG_INVALID", "项目测试团队 project_id 无效；未覆盖原文件")
        product_id = override.get("product_id")
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            raise TestingTeamError("TESTING_TEAM_CONFIG_INVALID", "项目测试团队 product_id 无效；未覆盖原文件")
        _validate_members(override.get("members"), "项目测试团队")


def _store_error(code: str, message: str, details: dict[str, object]) -> Exception:
    mapped = {
        "UNSAFE": "TESTING_TEAM_CONFIG_UNSAFE",
        "INVALID": "TESTING_TEAM_CONFIG_INVALID",
        "BUSY": "TESTING_TEAM_CONFIG_BUSY",
    }.get(code, "TESTING_TEAM_CONFIG_INVALID")
    return TestingTeamError(mapped, message, details)


class TestingTeamStore:
    """User-scope testing-team data, separate from personal ``teams`` data."""

    def __init__(self, identity: dict[str, str], *, root: Path | None = None):
        self._store = IdentityScopedJsonStore(
            identity,
            namespace="testing-teams",
            schema_version=SCHEMA_VERSION,
            max_bytes=MAX_CONFIG_BYTES,
            validator=lambda data: _validate_config(data, self._store.identity),
            root=root,
            error_factory=_store_error,
        )
        self.identity = dict(self._store.identity)
        self.root = self._store.root
        self.directory = self._store.directory
        self.path = self._store.path

    def read(self) -> dict[str, Any]:
        data = self._store.read()
        return empty_config(self.identity) if not data else data

    def update(self, transform: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        def wrapped(data: dict[str, Any]) -> dict[str, Any]:
            return transform(empty_config(self.identity) if not data else data)
        return self._store.update(wrapped)


def _users(client: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for browse in ("inside", "outside"):
        try:
            result = client.list_all("user", browse=browse, per_page=1000, preserve_partial=True)
        except Exception as exc:
            raise TestingTeamError("TESTING_TEAM_DIRECTORY_READ_FAILED", "无法读取完整用户目录；未修改测试团队") from exc
        partial = list(getattr(result, "partial_failures", []) or [])
        if getattr(result, "complete", False) is not True or partial:
            raise TestingTeamError("TESTING_TEAM_DIRECTORY_INCOMPLETE", "完整用户目录不可用；未修改测试团队",
                                    {"browse": browse, "partial_failures": partial})
        page_rows = getattr(result, "items", None)
        if not isinstance(page_rows, list) or any(not isinstance(row, dict) for row in page_rows):
            raise TestingTeamError("TESTING_TEAM_DIRECTORY_INVALID", "用户目录格式无效；未修改测试团队")
        rows.extend(page_rows)
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        account = row.get("account")
        if not valid_account(account):
            raise TestingTeamError("TESTING_TEAM_DIRECTORY_INVALID", "用户目录存在无效 account；未修改测试团队")
        previous = unique.get(account)
        if previous is not None and previous != row:
            raise TestingTeamError("TESTING_TEAM_DIRECTORY_CONFLICT", "用户目录存在 account 冲突；未修改测试团队",
                                    {"account": account})
        unique[account] = row
    if not any(account == client.account for account in unique):
        raise TestingTeamError("TESTING_TEAM_OWNER_UNAVAILABLE", "完整用户目录中未找到当前账号；未修改测试团队")
    return list(unique.values())


def _resolve_members(client: object, values: list[object]) -> list[str]:
    users = _users(client)
    resolved: set[str] = set()
    for value in values:
        try:
            row = resolve_user(users, value)
        except AmbiguousMatchError as exc:
            raise TestingTeamError("TESTING_TEAM_USER_AMBIGUOUS", "测试团队成员候选不唯一；未修改测试团队",
                                    {"value": value}) from exc
        except MatchNotFoundError as exc:
            raise TestingTeamError("TESTING_TEAM_USER_NOT_FOUND", "未找到测试团队成员；未修改测试团队",
                                    {"value": value}) from exc
        account = row.get("account")
        if not valid_account(account):
            raise TestingTeamError("TESTING_TEAM_USER_INVALID", "测试团队成员缺少真实 account；未修改测试团队")
        if account != client.account:
            resolved.add(account)
    return sorted(resolved)


def _project(data: dict[str, Any], alias: object) -> tuple[str, dict[str, Any]]:
    try:
        return _lookup_project(data, alias)
    except TestingConfigError as exc:
        code = "TESTING_PROJECT_NOT_FOUND" if exc.code == "PROJECT_NOT_FOUND" else "TESTING_PROJECT_CONFIG_INVALID"
        raise TestingTeamError(code, str(exc), getattr(exc, "details", {})) from exc


def _project_data(client: object, alias: object, root: Path | None) -> tuple[str, dict[str, Any]]:
    project_store = TestingProjectStore(client.connection_identity, root=root)
    return _project(project_store.read(), alias)


def _current_project_alias(client: object, root: Path | None) -> str | None:
    data = TestingProjectStore(client.connection_identity, root=root).read()
    current = data.get("current", {})
    alias = current.get("project_alias") if isinstance(current, dict) else None
    return alias if isinstance(alias, str) else None


def _override_matches(override: dict[str, Any], project: dict[str, Any]) -> bool:
    return (override.get("project_id") == project.get("project_id")
            and override.get("product_id") == project.get("product_id"))


def _result(client: object, data: dict[str, Any], *, source: str, configured: list[str],
            project_alias: str | None = None, override_exists: bool | None = None,
            failures: list[dict[str, object]] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    partial_failures = list(failures or [])
    payload: dict[str, Any] = {
        "team_domain": "testing",
        "source": source,
        "project_alias": project_alias,
        "configured_accounts": list(configured),
        "effective_accounts": [client.account, *configured] if client.account not in configured else list(configured),
        "complete": not partial_failures,
        "partial_failures": partial_failures,
    }
    if override_exists is not None:
        payload["override_exists"] = override_exists
    if extra:
        payload.update(extra)
    return payload


def _global_result(client: object, data: dict[str, Any], *, source: str = "global_default",
                   extra: dict[str, Any] | None = None) -> dict[str, Any]:
    members = list(data["global_default"]["members"])
    return _result(client, data, source=source, configured=members, extra=extra)


def effective_testing_team(client: object, *, project_alias: str | None = None,
                           root: Path | None = None) -> dict[str, Any]:
    """Resolve the configured team for a project, with global fallback."""
    store = TestingTeamStore(client.connection_identity, root=root)
    data = store.read()
    alias = project_alias if project_alias is not None else _current_project_alias(client, root)
    if alias is None:
        return _global_result(client, data)
    project_alias_value, project = _project_data(client, alias, root)
    override = data["project_overrides"].get(project_alias_value)
    if override is None:
        return _result(client, data, source="global_default", configured=list(data["global_default"]["members"]),
                       project_alias=project_alias_value, override_exists=False)
    if not _override_matches(override, project):
        return _result(client, data, source="global_default", configured=list(data["global_default"]["members"]),
                       project_alias=project_alias_value, override_exists=True,
                       failures=[{"code": "TESTING_TEAM_PROJECT_OVERRIDE_STALE", "project_alias": project_alias_value}])
    return _result(client, data, source="project_override", configured=list(override["members"]),
                   project_alias=project_alias_value, override_exists=True)


def view_testing_team(client: object, *, project_alias: str | None = None,
                      root: Path | None = None) -> dict[str, Any]:
    if project_alias is None:
        return _global_result(client, TestingTeamStore(client.connection_identity, root=root).read())
    return effective_testing_team(client, project_alias=project_alias, root=root)


def _update_global(client: object, operation: str, members: list[object], *, root: Path | None = None,
                   source: str = "global_default") -> dict[str, Any]:
    if operation not in {"add", "remove", "replace"}:
        raise TestingTeamError("TESTING_TEAM_OPERATION_INVALID", "测试团队操作无效；未修改测试团队")
    resolved = _resolve_members(client, members)
    store = TestingTeamStore(client.connection_identity, root=root)

    def transform(data: dict[str, Any]) -> dict[str, Any]:
        updated = copy.deepcopy(data)
        old = set(updated["global_default"]["members"])
        incoming = set(resolved)
        if operation == "add":
            result = old | incoming
        elif operation == "remove":
            result = old - incoming
        else:
            result = incoming
        updated["global_default"]["members"] = sorted(result)
        return updated

    return _global_result(client, store.update(transform), source=source)


def replace_global_team(client: object, members: list[object], *, root: Path | None = None) -> dict[str, Any]:
    return _update_global(client, "replace", members, root=root)


def add_global_team(client: object, members: list[object], *, root: Path | None = None) -> dict[str, Any]:
    return _update_global(client, "add", members, root=root)


def remove_global_team(client: object, members: list[object], *, root: Path | None = None) -> dict[str, Any]:
    return _update_global(client, "remove", members, root=root)


def _update_project(client: object, project_alias: object, operation: str, members: list[object], *,
                    root: Path | None = None) -> dict[str, Any]:
    if operation not in {"add", "remove", "replace"}:
        raise TestingTeamError("TESTING_TEAM_OPERATION_INVALID", "项目测试团队操作无效；未修改测试团队")
    alias, project = _project_data(client, project_alias, root)
    store = TestingTeamStore(client.connection_identity, root=root)
    current = store.read()
    if operation == "remove" and alias not in current["project_overrides"]:
        return _result(client, current, source="global_default",
                       configured=list(current["global_default"]["members"]),
                       project_alias=alias, override_exists=False)
    resolved = _resolve_members(client, members)

    def transform(data: dict[str, Any]) -> dict[str, Any]:
        updated = copy.deepcopy(data)
        overrides = updated["project_overrides"]
        previous = overrides.get(alias)
        old = set(previous.get("members", [])) if isinstance(previous, dict) else set()
        incoming = set(resolved)
        if operation == "add":
            result = old | incoming
        elif operation == "remove":
            result = old - incoming
        else:
            result = incoming
        overrides[alias] = {
            "project_alias": alias,
            "project_id": project.get("project_id"),
            "product_id": project.get("product_id"),
            "members": sorted(result),
        }
        return updated

    data = store.update(transform)
    return _result(client, data, source="project_override", project_alias=alias,
                   configured=list(data["project_overrides"][alias]["members"]), override_exists=True)


def replace_project_team(client: object, project_alias: object, members: list[object], *,
                         root: Path | None = None) -> dict[str, Any]:
    return _update_project(client, project_alias, "replace", members, root=root)


def add_project_team(client: object, project_alias: object, members: list[object], *,
                     root: Path | None = None) -> dict[str, Any]:
    return _update_project(client, project_alias, "add", members, root=root)


def remove_project_team(client: object, project_alias: object, members: list[object], *,
                        root: Path | None = None) -> dict[str, Any]:
    return _update_project(client, project_alias, "remove", members, root=root)


def remove_project_team_override(client: object, project_alias: object, *, root: Path | None = None) -> dict[str, Any]:
    alias, _ = _project_data(client, project_alias, root)
    store = TestingTeamStore(client.connection_identity, root=root)
    current = store.read()
    if alias not in current["project_overrides"]:
        raise TestingTeamError("TESTING_TEAM_OVERRIDE_NOT_FOUND", "未找到项目测试团队覆盖；未修改测试团队",
                               {"project_alias": alias})

    def transform(data: dict[str, Any]) -> dict[str, Any]:
        updated = copy.deepcopy(data)
        if alias not in updated["project_overrides"]:
            raise TestingTeamError("TESTING_TEAM_OVERRIDE_NOT_FOUND", "未找到项目测试团队覆盖；未修改测试团队",
                                   {"project_alias": alias})
        del updated["project_overrides"][alias]
        return updated

    store.update(transform)
    return effective_testing_team(client, project_alias=alias, root=root) | {
        "removed_project_alias": alias,
        "source": "global_default",
        "override_exists": False,
        "complete": True,
        "partial_failures": [],
    }


def _personal_team_store(identity: dict[str, str]):
    path = REPO_ROOT / "skills" / "zentao-personal" / "scripts" / "team_config.py"
    spec = importlib.util.spec_from_file_location("_zentao_personal_team_config_for_import", path)
    if spec is None or spec.loader is None:
        raise TestingTeamError("PERSONAL_TEAM_UNAVAILABLE", "无法读取开发/个人团队配置；未修改测试团队")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        return module.TeamStore(identity)
    except Exception as exc:
        raise TestingTeamError("PERSONAL_TEAM_UNAVAILABLE", "开发/个人团队配置不可用；未修改测试团队") from exc


def import_personal_team(client: object, *, root: Path | None = None) -> dict[str, Any]:
    personal = _personal_team_store(client.connection_identity)
    try:
        configured = personal.read()
    except Exception as exc:
        raise TestingTeamError("PERSONAL_TEAM_UNAVAILABLE", "开发/个人团队配置不可用；未修改测试团队") from exc
    result = _update_global(client, "replace", configured, root=root, source="explicit_personal_import")
    result["imported_from"] = "personal/development_team"
    return result


__all__ = [
    "TestingTeamError", "TestingTeamStore", "add_global_team", "add_project_team",
    "effective_testing_team", "empty_config", "import_personal_team", "remove_global_team",
    "remove_project_team", "remove_project_team_override", "replace_global_team",
    "replace_project_team", "valid_account", "view_testing_team",
]
