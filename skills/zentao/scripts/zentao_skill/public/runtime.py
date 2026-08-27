from __future__ import annotations

from pathlib import Path

from ..internal import config


def prepare_runtime_temp_root() -> Path:
    """Return the current private runtime temp root for read-only high-level helpers."""
    paths = config.resolve_runtime_paths()
    if paths.scope == "user":
        config.ensure_private_directory(paths.temp_root.parent)
    config.ensure_private_directory(paths.temp_root)
    return paths.temp_root
