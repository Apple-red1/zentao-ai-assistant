from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zentao_ai.repository import RepositoryMapping, preflight_repository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--config", required=True)
    preflight.add_argument("--scope-json", required=True)
    args = parser.parse_args()
    try:
        raw = json.loads(args.scope_json)
        mapping = RepositoryMapping.model_validate(raw)
        result = preflight_repository(mapping)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        payload = {
            "allowed": False, "reasons": ["INVALID_SCOPE_JSON"],
            "repository": "", "path": "", "branch": None, "head": None,
            "ahead": None, "behind": None, "testCommands": [], "error": str(error),
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 2
    print(result.model_dump_json())
    return 0 if result.allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
