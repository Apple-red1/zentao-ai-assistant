from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[2]


def test_project_metadata_matches_public_contract() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        project = tomllib.load(project_file)["project"]

    assert project["name"] == "zentao-ai-assistant"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.11"


def test_package_exposes_typed_version() -> None:
    import zentao_ai

    assert zentao_ai.__version__ == "0.1.0"
    assert zentao_ai.__annotations__["__version__"] is str


def test_console_entry_point_resolves_to_main() -> None:
    entry_point = next(
        entry_point
        for entry_point in importlib.metadata.entry_points(group="console_scripts")
        if entry_point.name == "zentao-ai"
    )

    assert entry_point.value == "zentao_ai.cli.app:main"
    assert callable(entry_point.load())
