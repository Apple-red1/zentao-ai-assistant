from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zentao_ai.config import load_config  # noqa: E402
from zentao_ai.repository import RepositoryMapping, preflight_repository  # noqa: E402


def norm(value: object) -> str:
    return unicodedata.normalize("NFC", str(value)).strip().casefold()


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
    print(json.dumps(payload, ensure_ascii=False))
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
        raw = json.loads(args.scope_json)
        if not isinstance(raw, dict):
            raise ValueError("scope must be object")
        values = {
            norm(value)
            for value in raw.values()
            if isinstance(value, (str, int)) and norm(value)
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return output(["CONFIG_INVALID"])
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
        scopeName=key,
        matchedRepositoryCount=1,
        repositoryKey=key,
        repositoryName=item.repository,
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
