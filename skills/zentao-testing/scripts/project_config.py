"""Persistent testing-project context and deterministic validation."""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED = REPO_ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.identity import AmbiguousMatchError, MatchNotFoundError, resolve_user  # noqa: E402
from zentao.identity_store import IdentityScopedJsonStore  # noqa: E402


SCHEMA_VERSION = 1
MAX_CONFIG_BYTES = 1024 * 1024


class TestingConfigError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def positive_id(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise TestingConfigError("ID_INVALID", f"{label} 必须是正整数")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and value and all("0" <= char <= "9" for char in value):
        result = int(value)
    else:
        raise TestingConfigError("ID_INVALID", f"{label} 必须是正整数")
    if result <= 0:
        raise TestingConfigError("ID_INVALID", f"{label} 必须是正整数")
    return result


def validate_alias(value: object, label: str = "别名") -> str:
    if not isinstance(value, str):
        raise TestingConfigError("ALIAS_INVALID", f"{label} 必须是文本")
    if value != value.strip() or not value or any(ord(char) < 32 for char in value):
        raise TestingConfigError("ALIAS_INVALID", f"{label} 不能为空、不能含控制字符或首尾空白")
    if len(value) > 80:
        raise TestingConfigError("ALIAS_INVALID", f"{label} 不能超过 80 个字符")
    return value

def validate_build(value: object) -> str | int:
    if value == "trunk":
        return "trunk"
    return positive_id(value, "affected-build")

def empty_config(identity: dict[str, str]) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "owner": dict(identity), "projects": {},
            "current": {"project_alias": None, "module_alias": None}}


def _validate_config(data: dict[str, Any], identity: dict[str, str]) -> None:
    if data.get("owner") != identity or not isinstance(data.get("projects"), dict):
        raise TestingConfigError("CONFIG_INVALID", "测试项目配置归属或 projects 无效；未覆盖原文件")
    current = data.get("current")
    if not isinstance(current, dict):
        raise TestingConfigError("CONFIG_INVALID", "测试项目 current 无效；未覆盖原文件")
    for field in ("project_alias", "module_alias"):
        if current.get(field) is not None:
            validate_alias(current[field], field)
    project_aliases: set[str] = set()
    for alias, project in data["projects"].items():
        validate_alias(alias, "项目别名")
        folded_alias = alias.casefold()
        if folded_alias in project_aliases:
            raise TestingConfigError("CONFIG_INVALID", "项目别名大小写冲突；未覆盖原文件")
        project_aliases.add(folded_alias)
        if not isinstance(project, dict):
            raise TestingConfigError("CONFIG_INVALID", "项目配置无效；未覆盖原文件")
        if project.get("project_id") is not None:
            positive_id(project.get("project_id"), "project_id")
        positive_id(project.get("product_id"), "product_id")
        validate_build(project.get("default_affected_build"))
        verification = project.get("verification")
        if not isinstance(verification, dict) or verification.get("project_product") not in {"verified", "unverified", "not_applicable"}:
            raise TestingConfigError("CONFIG_INVALID", "项目 verification 无效；未覆盖原文件")
        modules = project.get("modules")
        if not isinstance(modules, dict):
            raise TestingConfigError("CONFIG_INVALID", "项目 modules 无效；未覆盖原文件")
        module_aliases: set[str] = set()
        for module_alias, module in modules.items():
            validate_alias(module_alias, "模块别名")
            folded_module_alias = module_alias.casefold()
            if folded_module_alias in module_aliases:
                raise TestingConfigError("CONFIG_INVALID", "模块别名大小写冲突；未覆盖原文件")
            module_aliases.add(folded_module_alias)
            if not isinstance(module, dict):
                raise TestingConfigError("CONFIG_INVALID", "模块配置无效；未覆盖原文件")
            positive_id(module.get("module_id"), "module_id")
            for field in ("frontend_account", "backend_account"):
                value = module.get(field)
                if (not isinstance(value, str) or not value or value != value.strip()
                        or value.casefold() == "closed"):
                    raise TestingConfigError("CONFIG_INVALID", f"{field} 无效；未覆盖原文件")
            if "stale" in module and type(module["stale"]) is not bool:
                raise TestingConfigError("CONFIG_INVALID", "模块 stale 标记无效；未覆盖原文件")
            module_verification = module.get("verification")
            if not isinstance(module_verification, dict) or module_verification.get("module") not in {"verified", "unverified"}:
                raise TestingConfigError("CONFIG_INVALID", "模块 verification 无效；未覆盖原文件")
    project_alias = current.get("project_alias")
    module_alias = current.get("module_alias")
    if project_alias is not None and project_alias not in data["projects"]:
        raise TestingConfigError("CONFIG_INVALID", "current 引用了不存在的项目；未覆盖原文件")
    if module_alias is not None:
        if project_alias is None or module_alias not in data["projects"][project_alias]["modules"]:
            raise TestingConfigError("CONFIG_INVALID", "current 引用了不存在的模块；未覆盖原文件")


def _store_error(code: str, message: str, details: dict[str, object]) -> Exception:
    mapped = {"UNSAFE": "CONFIG_UNSAFE", "INVALID": "CONFIG_INVALID", "BUSY": "CONFIG_BUSY"}.get(code, code)
    return TestingConfigError(mapped, message, details)


class TestingProjectStore:
    """Testing configuration in its own user-scope namespace."""
    def __init__(self, identity: dict[str, str], *, root: Path | None = None):
        self._store = IdentityScopedJsonStore(
            identity,
            namespace="testing-projects",
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

    def update(self, transform) -> dict[str, Any]:
        def wrapped(data: dict[str, Any]) -> dict[str, Any]:
            return transform(empty_config(self.identity) if not data else data)
        return self._store.update(wrapped)


def _list_all(client: object, resource: str, **kwargs: object) -> list[dict[str, Any]]:
    try:
        result = client.list_all(resource, preserve_partial=True, **kwargs)
    except TestingConfigError:
        raise
    except Exception as exc:
        raise TestingConfigError("DIRECTORY_READ_FAILED", f"无法读取 {resource} 候选集合") from exc
    if not getattr(result, "complete", False):
        raise TestingConfigError("DIRECTORY_INCOMPLETE", f"{resource} 候选集合不完整，未保存配置",
                                 {"resource": resource, "partial_failures": getattr(result, "partial_failures", [])})
    rows = getattr(result, "items", None)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise TestingConfigError("DIRECTORY_INVALID", f"{resource} 候选集合格式无效，未保存配置")
    unique: dict[int, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    for row in rows:
        row_id = _record_id(row)
        if row_id is None:
            raise TestingConfigError("DIRECTORY_INVALID", f"{resource} 候选缺少合法 ID，未保存配置")
        previous = unique.get(row_id)
        if previous is not None:
            if previous != row:
                raise TestingConfigError("DIRECTORY_CONFLICT", f"{resource} 候选存在冲突重复 ID，未保存配置",
                                         {"id": row_id})
            continue
        unique[row_id] = row
        ordered.append(row)
    return ordered

def _record_id(row: dict[str, Any]) -> int | None:
    try:
        return positive_id(row.get("id"), "id")
    except TestingConfigError:
        return None

def _resolve_entity(rows: list[dict[str, Any]], value: object, kind: str) -> dict[str, Any]:
    try:
        wanted_id = positive_id(value, kind)
    except TestingConfigError:
        wanted_id = None
    if wanted_id is not None:
        matches = [row for row in rows if _record_id(row) == wanted_id]
    else:
        if not isinstance(value, str) or value != value.strip() or not value:
            raise TestingConfigError("ENTITY_NOT_FOUND", f"未找到{kind}")
        matches = [row for row in rows if row.get("name") == value or row.get("title") == value]
    if len(matches) > 1:
        raise TestingConfigError("ENTITY_AMBIGUOUS", f"{kind} 候选不唯一", {"value": value})
    if not matches:
        raise TestingConfigError("ENTITY_NOT_FOUND", f"未找到{kind}", {"value": value})
    return matches[0]

def _contains_id(value: object, expected: int) -> bool:
    if not isinstance(value, bool) and isinstance(value, int) and value == expected:
        return True
    if isinstance(value, str) and value.isascii() and value.isdigit() and int(value) == expected:
        return True
    if isinstance(value, dict):
        if _record_id(value) == expected:
            return True
        return any(_contains_id(item, expected) for item in value.values())
    if isinstance(value, list):
        return any(_contains_id(item, expected) for item in value)
    return False

def _relationship(project: dict[str, Any] | None, product: dict[str, Any], product_id: int) -> str:
    if project is None:
        return "not_applicable"
    relation_keys = {"product", "products", "productID", "productId", "product_ids", "productIds"}
    project_evidence = any(key in project for key in relation_keys)
    product_evidence = any(key in product for key in {"project", "projects", "projectID", "projectId", "project_ids", "projectIds"})
    if (project_evidence and _contains_id({key: project.get(key) for key in relation_keys if key in project}, product_id)):
        return "verified"
    if product_evidence and _contains_id({key: product.get(key) for key in ("project", "projects", "projectID", "projectId", "project_ids", "projectIds") if key in product}, positive_id(project.get("id"), "project_id")):
        return "verified"
    if project_evidence or product_evidence:
        raise TestingConfigError("PROJECT_PRODUCT_MISMATCH", "Project 与 Product 关联不匹配，未保存配置")
    return "unverified"

def _build_status(client: object, project_id: int | None, value: object) -> str | None:
    if value == "trunk":
        return None
    wanted = positive_id(value, "affected-build")
    if project_id is None:
        return None
    rows = _list_all(client, "build", scope="project", scope_id=project_id, browse="all")
    if not any(_record_id(row) == wanted for row in rows):
        raise TestingConfigError("BUILD_NOT_FOUND", "affected-build 不属于该 Project，未保存配置", {"build_id": wanted})
    return None

def _module_relationship(payload: object, module_id: int) -> str:
    """Use only explicit module collections returned by a product view."""
    if not isinstance(payload, dict):
        return "unverified"
    evidence = False
    for key in ("modules", "module", "submodules"):
        if key in payload:
            evidence = True
            if _contains_id(payload[key], module_id):
                return "verified"
    for key in ("product", "data"):
        if isinstance(payload.get(key), dict):
            nested = _module_relationship(payload[key], module_id)
            if nested == "verified":
                return nested
            evidence = evidence or nested == "mismatch"
    return "mismatch" if evidence else "unverified"

def _module_status(client: object, product_id: int, module_id: int) -> str:
    try:
        payload = client.view("product", product_id)
    except Exception:
        return "unverified"
    return _module_relationship(payload, module_id)

def _users(client: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for browse in ("inside", "outside"):
        rows.extend(_list_all(client, "user", browse=browse))
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        account = row.get("account")
        if not isinstance(account, str) or not account or account != account.strip():
            raise TestingConfigError("USER_DIRECTORY_INVALID", "用户目录存在无效 account，未保存配置")
        previous = unique.get(account)
        if previous is not None and previous != row:
            raise TestingConfigError("USER_DIRECTORY_INCOMPLETE", "用户目录存在 account 冲突，未保存配置")
        unique[account] = row
    return list(unique.values())

def _resolve_account(client: object, value: object) -> str:
    try:
        row = resolve_user(_users(client), value)
    except AmbiguousMatchError as exc:
        raise TestingConfigError("USER_AMBIGUOUS", "负责人候选不唯一，未保存配置", {"value": value}) from exc
    except MatchNotFoundError as exc:
        raise TestingConfigError("USER_NOT_FOUND", "未找到负责人，未保存配置", {"value": value}) from exc
    account = row.get("account")
    if not isinstance(account, str) or not account or account.casefold() == "closed":
        raise TestingConfigError("USER_INVALID", "负责人缺少真实 account，未保存配置")
    return account

def _lookup_project(data: dict[str, Any], alias: object) -> tuple[str, dict[str, Any]]:
    name = validate_alias(alias, "项目别名")
    matches = [key for key in data["projects"] if key.casefold() == name.casefold()]
    if len(matches) > 1 or (matches and matches[0] != name):
        raise TestingConfigError("ALIAS_CONFLICT", "项目别名大小写冲突")
    if not matches:
        raise TestingConfigError("PROJECT_NOT_FOUND", "未找到测试项目", {"alias": name})
    return matches[0], data["projects"][matches[0]]


def _lookup_module(project: dict[str, Any], alias: object) -> tuple[str, dict[str, Any]]:
    name = validate_alias(alias, "模块别名")
    matches = [key for key in project["modules"] if key.casefold() == name.casefold()]
    if len(matches) > 1 or (matches and matches[0] != name):
        raise TestingConfigError("ALIAS_CONFLICT", "模块别名大小写冲突")
    if not matches:
        raise TestingConfigError("MODULE_NOT_FOUND", "未找到测试模块", {"alias": name})
    return matches[0], project["modules"][matches[0]]


def project_set(client: object, *, alias: object, project: object, product: object, default_build: object,
                root: Path | None = None) -> dict[str, Any]:
    name = validate_alias(alias, "项目别名")
    projects = _list_all(client, "project", browse="all") if project is not None else []
    products = _list_all(client, "product", browse="all")
    project_row = _resolve_entity(projects, project, "Project") if project is not None else None
    product_row = _resolve_entity(products, product, "Product")
    project_id = positive_id(project_row.get("id"), "project_id") if project_row else None
    product_id = positive_id(product_row.get("id"), "product_id")
    relationship = _relationship(project_row, product_row, product_id)
    _build_status(client, project_id, default_build)
    build = validate_build(default_build)
    store = TestingProjectStore(client.connection_identity, root=root)
    failures = []
    if relationship == "unverified":
        failures.append({"code": "PROJECT_PRODUCT_UNVERIFIED", "message": "当前只读能力未返回 Project/Product 关联证据"})

    def transform(data: dict[str, Any]) -> dict[str, Any]:
        data = copy.deepcopy(data)
        alias_matches = [key for key in data["projects"] if key.casefold() == name.casefold()]
        if alias_matches and alias_matches[0] != name:
            raise TestingConfigError("ALIAS_CONFLICT", "项目别名大小写冲突")
        previous = data["projects"].get(name)
        modules = copy.deepcopy(previous.get("modules", {})) if isinstance(previous, dict) else {}
        changed = not previous or any(previous.get(key) != value for key, value in (
            ("project_id", project_id), ("product_id", product_id), ("default_affected_build", build)))
        if changed:
            for module in modules.values():
                module["stale"] = True
        data["projects"][name] = {"project_id": project_id, "product_id": product_id,
            "default_affected_build": build, "modules": modules,
            "verification": {"project_product": relationship}}
        return data

    data = store.update(transform)
    result = context_view_from_data(data, allow_missing=True)
    result.update({"saved_project_alias": name, "project": data["projects"][name], "complete": not failures,
                   "partial_failures": failures})
    return result


def project_remove(client: object, alias: object, *, root: Path | None = None) -> dict[str, Any]:
    store = TestingProjectStore(client.connection_identity, root=root)
    def transform(data: dict[str, Any]) -> dict[str, Any]:
        data = copy.deepcopy(data)
        name, _ = _lookup_project(data, alias)
        del data["projects"][name]
        if data["current"].get("project_alias") == name:
            data["current"] = {"project_alias": None, "module_alias": None}
        return data
    return context_view_from_data(store.update(transform), allow_missing=True)


def project_list(client: object, *, root: Path | None = None) -> dict[str, Any]:
    store = TestingProjectStore(client.connection_identity, root=root)
    data = store.read()
    items = []
    failures: list[dict[str, object]] = []
    for alias, project in sorted(data["projects"].items(), key=lambda item: item[0].casefold()):
        if project["verification"].get("project_product") not in {"verified", "not_applicable"}:
            failures.append({"code": "PROJECT_PRODUCT_UNVERIFIED", "project_alias": alias})
        for module_alias, module in project["modules"].items():
            if module["verification"].get("module") != "verified":
                failures.append({"code": "MODULE_UNVERIFIED", "project_alias": alias,
                                 "module_alias": module_alias})
            if module.get("stale"):
                failures.append({"code": "MODULE_STALE", "project_alias": alias,
                                 "module_alias": module_alias})
        items.append({"alias": alias, "project_id": project["project_id"], "product_id": project["product_id"],
                      "default_affected_build": project["default_affected_build"],
                      "module_aliases": sorted(project["modules"], key=str.casefold),
                      "stale_modules": sorted(alias for alias, value in project["modules"].items() if value.get("stale")),
                      "verification": copy.deepcopy(project["verification"]),
                      "module_verification": {module_alias: copy.deepcopy(module["verification"])
                                              for module_alias, module in sorted(project["modules"].items(),
                                                                                 key=lambda item: item[0].casefold())}})
    return {"current": dict(data["current"]), "projects": items, "complete": not failures,
            "partial_failures": failures}


def module_set(client: object, *, project_alias: object, alias: object, module: object,
               frontend: object, backend: object, root: Path | None = None) -> dict[str, Any]:
    module_name = validate_alias(alias, "模块别名")
    module_id = positive_id(module, "module_id")
    _, project = _lookup_project(TestingProjectStore(client.connection_identity, root=root).read(), project_alias)
    product_id = positive_id(project.get("product_id"), "product_id")
    frontend_account = _resolve_account(client, frontend)
    backend_account = _resolve_account(client, backend)
    store = TestingProjectStore(client.connection_identity, root=root)
    module_status = _module_status(client, product_id, module_id)
    if module_status == "mismatch":
        raise TestingConfigError("MODULE_PRODUCT_MISMATCH", "Module 不属于所选 Product，未保存配置")
    failures = [] if module_status == "verified" else [
        {"code": "MODULE_UNVERIFIED", "message": "当前只读能力未返回可证明的 Product 模块关联证据"}]
    def transform(data: dict[str, Any]) -> dict[str, Any]:
        data = copy.deepcopy(data)
        project_name, project_data = _lookup_project(data, project_alias)
        existing = [key for key in project_data["modules"] if key.casefold() == module_name.casefold()]
        if existing and existing[0] != module_name:
            raise TestingConfigError("ALIAS_CONFLICT", "模块别名大小写冲突")
        project_data["modules"][module_name] = {"module_id": module_id,
            "frontend_account": frontend_account, "backend_account": backend_account,
            "stale": False, "verification": {"module": module_status}}
        data["projects"][project_name] = project_data
        return data
    data = store.update(transform)
    _, saved_project = _lookup_project(data, project_alias)
    result = context_view_from_data(data, allow_missing=True)
    operation_failures = list(failures)
    if saved_project["verification"].get("project_product") not in {"verified", "not_applicable"}:
        operation_failures.insert(0, {"code": "PROJECT_PRODUCT_UNVERIFIED",
                                      "message": "Project 与 Product 关联尚未被只读证据验证"})
    result.update({"saved_module_alias": module_name, "module": saved_project["modules"][module_name],
                   "complete": not operation_failures, "partial_failures": operation_failures})
    return result


def module_remove(client: object, *, project_alias: object, alias: object, root: Path | None = None) -> dict[str, Any]:
    store = TestingProjectStore(client.connection_identity, root=root)
    def transform(data: dict[str, Any]) -> dict[str, Any]:
        data = copy.deepcopy(data)
        project_name, project = _lookup_project(data, project_alias)
        module_name, _ = _lookup_module(project, alias)
        del project["modules"][module_name]
        if data["current"].get("project_alias") == project_name and data["current"].get("module_alias") == module_name:
            data["current"]["module_alias"] = None
        return data
    return context_view_from_data(store.update(transform), allow_missing=True)


def context_use(client: object, *, project_alias: object, module_alias: object, root: Path | None = None) -> dict[str, Any]:
    store = TestingProjectStore(client.connection_identity, root=root)
    def transform(data: dict[str, Any]) -> dict[str, Any]:
        data = copy.deepcopy(data)
        project_name, project = _lookup_project(data, project_alias)
        module_name, _ = _lookup_module(project, module_alias)
        data["current"] = {"project_alias": project_name, "module_alias": module_name}
        return data
    return context_view_from_data(store.update(transform), allow_missing=False)


def context_view(client: object, *, root: Path | None = None) -> dict[str, Any]:
    return context_view_from_data(TestingProjectStore(client.connection_identity, root=root).read(), allow_missing=False)


def context_view_from_data(data: dict[str, Any], *, allow_missing: bool) -> dict[str, Any]:
    current = dict(data["current"])
    project_alias = current.get("project_alias")
    module_alias = current.get("module_alias")
    result: dict[str, Any] = {"current": current, "complete": True, "partial_failures": []}
    if project_alias is None:
        if not allow_missing:
            raise TestingConfigError("CURRENT_CONTEXT_MISSING", "尚未设置当前测试项目")
        result["complete"] = False
        result["partial_failures"].append({"code": "CURRENT_CONTEXT_MISSING", "message": "尚未设置当前测试项目"})
        return result
    project = data["projects"].get(project_alias)
    if project is None:
        raise TestingConfigError("CONFIG_INVALID", "current 项目不存在")
    result["project"] = project
    if project.get("verification", {}).get("project_product") not in {"verified", "not_applicable"}:
        result["complete"] = False
        result["partial_failures"].append({"code": "PROJECT_PRODUCT_UNVERIFIED",
                                            "message": "Project 与 Product 关联尚未被只读证据验证"})
    if module_alias is None:
        if not allow_missing:
            raise TestingConfigError("CURRENT_MODULE_MISSING", "尚未设置当前测试模块")
        result["complete"] = False
        result["partial_failures"].append({"code": "CURRENT_MODULE_MISSING", "message": "尚未设置当前测试模块"})
        return result
    module = project["modules"].get(module_alias)
    if module is None:
        raise TestingConfigError("CONFIG_INVALID", "current 模块不存在")
    result["module"] = module
    if module.get("verification", {}).get("module") != "verified":
        result["complete"] = False
        result["partial_failures"].append({"code": "MODULE_UNVERIFIED",
                                            "message": "Module 与 Product 关联尚未被只读证据验证"})
    if module.get("stale"):
        result["complete"] = False
        result["partial_failures"].append({"code": "MODULE_STALE", "message": "当前模块需要重新验证"})
    return result


__all__ = ["TestingConfigError", "TestingProjectStore", "context_use", "context_view",
           "context_view_from_data", "empty_config", "module_remove", "module_set",
           "project_list", "project_remove", "project_set", "positive_id", "validate_alias", "validate_build"]
