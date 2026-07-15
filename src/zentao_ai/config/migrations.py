from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def migrate_config(data: Mapping[str, Any]) -> dict[str, Any]:
    migrated = deepcopy(dict(data))
    version = migrated.get("configVersion")
    if version is None:
        migrated["configVersion"] = 1
    elif version != 1:
        raise ValueError(f"unsupported configVersion: {version}")
    return migrated
