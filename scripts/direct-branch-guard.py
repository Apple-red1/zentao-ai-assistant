from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zentao_ai.config import load_config  # noqa: E402
from zentao_ai.repository import RepositoryMapping, preflight_repository  # noqa: E402
from zentao_ai.routing.router import normalize_scope_name  # noqa: E402


def norm(value: object) -> str:
    return normalize_scope_name(str(value))


def output(reason_codes: list[str], **values: Any) -> int:
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
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload))
    return 0 if not reason_codes else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("preflight")
    command.add_argument("--config", required=True)
    command.add_argument("--scope-json", required=True)
    args = parser.parse_args()
    try:
        config_path = Path(args.config).resolve(strict=True)
        config = load_config(config_path)
    except (OSError, ValueError, TypeError):
        return output(["CONFIG_INVALID"])
    try:
        raw = json.loads(args.scope_json)
        if not isinstance(raw, dict):
            raise ValueError("scope must be object")
        values = {
            norm(value)
            for value in raw.values()
            if isinstance(value, (str, int)) and norm(value)
        }
    except (ValueError, TypeError, json.JSONDecodeError):
        return output(["SCOPE_JSON_INVALID"])
    matches = [
        (key, item)
        for key, item in config.repositories.items()
        if norm(key) in values
    ]
    if not matches:
        return output(["REPOSITORY_SCOPE_NO_MATCH"], matchedRepositoryCount=0)
    if len(matches) != 1:
        return output(
            ["REPOSITORY_SCOPE_AMBIGUOUS"],
            matchedRepositoryCount=len(matches),
        )
    key, item = matches[0]
    repository_path = Path(item.path)
    if not repository_path.is_absolute():
        repository_path = config_path.parent / repository_path
    repository_path = repository_path.resolve()
    normalized_path = os.path.normcase(str(repository_path.resolve()))
    legacy_repository_key = hashlib.sha256(normalized_path.encode("utf-8")).hexdigest()
    result = preflight_repository(
        RepositoryMapping(
            repository=item.repository,
            path=repository_path,
            targetBranch=item.targetBranch,
            testCommands=tuple(item.testCommands),
            configPath=config_path,
            repositoryKey=key,
        )
    )
    return output(
        result.reasons,
        scopeName=normalize_scope_name(key),
        matchedRepositoryCount=1,
        repositoryKey=legacy_repository_key,
        repositoryName=repository_path.name,
        repositoryPath=result.path,
        upstream=result.upstream,
        dirtyEntryCount=result.dirtyEntryCount,
        ahead=result.ahead,
        behind=result.behind,
        head=result.head,
        branch=result.branch,
        testCommands=result.testCommands,
        indexFingerprint=result.indexFingerprint,
        worktreeFingerprint=result.worktreeFingerprint,
        preimageFingerprint=result.preimageFingerprint,
    )


if __name__ == "__main__":
    raise SystemExit(main())
