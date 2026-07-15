from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from zentao_ai.config import load_config
from zentao_ai.repository import RepositoryMapping, preflight_repository
from zentao_ai.routing.router import normalize_scope_name


def _norm(value: object) -> str:
    return normalize_scope_name(str(value))


def _output(reason_codes: list[str], **values: Any) -> int:
    payload = {
        "ok": not reason_codes,
        "reasonCodes": reason_codes,
        "scopeName": values.get("scopeName"),
        "matchedRepositoryCount": values.get("matchedRepositoryCount", 0),
        "repositoryKey": values.get("repositoryKey"),
        "repositoryName": values.get("repositoryName"),
        "repositoryPath": values.get("repositoryPath"),
        "upstream": values.get("upstream"),
        "dirtyEntryCount": values.get("dirtyEntryCount", 0),
    }
    payload.update(values)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if not reason_codes else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("preflight")
    command.add_argument("--config", required=True)
    command.add_argument("--scope-json", required=True)
    args = parser.parse_args(argv)
    try:
        config_path = Path(args.config).resolve(strict=True)
        config = load_config(config_path)
    except (OSError, ValueError, TypeError):
        return _output(["CONFIG_INVALID"])
    try:
        raw = json.loads(args.scope_json)
        if not isinstance(raw, dict):
            raise ValueError("scope must be object")
        values = {_norm(value) for value in raw.values() if isinstance(value, (str, int)) and _norm(value)}
    except (ValueError, TypeError, json.JSONDecodeError):
        return _output(["SCOPE_JSON_INVALID"])
    matches = [(key, item) for key, item in config.repositories.items() if _norm(key) in values]
    if not matches:
        return _output(["REPOSITORY_SCOPE_NO_MATCH"], matchedRepositoryCount=0)
    if len(matches) != 1:
        return _output(["REPOSITORY_SCOPE_AMBIGUOUS"], matchedRepositoryCount=len(matches))
    key, item = matches[0]
    repository_path = Path(item.path)
    if not repository_path.is_absolute():
        repository_path = config_path.parent / repository_path
    repository_path = repository_path.resolve()
    legacy_key = hashlib.sha256(os.path.normcase(str(repository_path)).encode("utf-8")).hexdigest()
    result = preflight_repository(RepositoryMapping(repository=item.repository, path=repository_path, targetBranch=item.targetBranch, testCommands=tuple(item.testCommands), configPath=config_path, repositoryKey=key))
    return _output(result.reasons, scopeName=normalize_scope_name(key), matchedRepositoryCount=1, repositoryKey=legacy_key, repositoryName=repository_path.name, repositoryPath=result.path, upstream=result.upstream, dirtyEntryCount=result.dirtyEntryCount, ahead=result.ahead, behind=result.behind, head=result.head, branch=result.branch, testCommands=result.testCommands, indexFingerprint=result.indexFingerprint, worktreeFingerprint=result.worktreeFingerprint, preimageFingerprint=result.preimageFingerprint)


if __name__ == "__main__":
    raise SystemExit(main())
