from __future__ import annotations

import json
import os
import stat
import sys
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ZENTAO_SCRIPTS = REPO_ROOT / "skills" / "zentao" / "scripts"
if str(ZENTAO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ZENTAO_SCRIPTS))

from zentao_skill.public import ListResult, ZentaoClient  # noqa: E402


def get_client() -> ZentaoClient:
    return ZentaoClient()


def store_temp_json(kind: str, payload: object) -> str:
    run_id = uuid.uuid4().hex
    directory = REPO_ROOT / ".tmp" / "zentao" / kind / run_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        directory.chmod(0o700)
    path = directory / "data.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise OSError("temporary data permissions are not private")
    finally:
        if fd >= 0:
            os.close(fd)
    return str(path)


__all__ = ["ListResult", "ZentaoClient", "get_client", "store_temp_json"]
