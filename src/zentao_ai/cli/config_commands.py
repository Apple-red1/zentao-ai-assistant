from __future__ import annotations

import os
import tempfile
from pathlib import Path

import typer
import yaml  # type: ignore[import-untyped]

app = typer.Typer(help="Manage project configuration.")


@app.command("init")
def init_config(
    path: Path = typer.Option(Path(".codex/zentao-ai-bug.yaml"), "--path"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Create a safe version-1 personal project configuration."""
    if path.exists() and not force:
        typer.echo("configuration already exists", err=True)
        raise typer.Exit(2)
    try:
        scope = typer.prompt("Scope name").strip()
    except (KeyboardInterrupt, typer.Abort):
        raise typer.Exit(130) from None
    if not scope:
        raise typer.BadParameter("scope name is required")
    payload = {
        "configVersion": 1,
        "zentao": {"baseUrl": None, "account": None},
        "personal": {"scopeNames": [scope]},
        "team": {"scopeNames": [scope], "members": []},
        "repositories": {
            scope: {
                "repository": scope,
                "path": ".",
                "targetBranch": "main",
                "testCommands": [],
            }
        },
        "permissions": {
            "codeWriteEnabled": False,
            "commentEnabled": False,
            "stepUpdateEnabled": False,
        },
    }
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".zentao-ai-", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    typer.echo("configuration initialized")
