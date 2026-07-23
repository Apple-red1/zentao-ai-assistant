from __future__ import annotations

import os
import tempfile
import json
from pathlib import Path

import typer
import yaml  # type: ignore[import-untyped]

from zentao_ai.config.models import AppConfig
from .runtime import emit, failure

app = typer.Typer(help="Manage project configuration.")


def _ask(label: str, default: str | None = None) -> str:
    try:
        return str(typer.prompt(label, default=default)).strip()
    except (KeyboardInterrupt, typer.Abort):
        raise typer.Exit(130) from None


@app.command("init")
def init_config(
    path: Path = typer.Option(Path(".codex/zentao-ai-bug.yaml"), "--path"),
    force: bool = typer.Option(False, "--force"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    if path.exists() and not force:
        if json_output:
            typer.echo(
                json.dumps(failure(2, "input", "configuration already exists", "path"))
            )
        else:
            typer.echo("Configuration already exists", err=True)
        raise typer.Exit(2)
    base_url = _ask("Zentao base URL")
    account = _ask("Zentao account")
    personal = tuple(
        x.strip()
        for x in _ask("Personal scopes (comma separated)").split(",")
        if x.strip()
    )
    team = tuple(
        x.strip()
        for x in _ask("Team scopes (comma separated)", ",".join(personal)).split(",")
        if x.strip()
    )
    members = [
        x.strip()
        for x in _ask("Team members (comma separated)", "").split(",")
        if x.strip()
    ]
    scopes = tuple(dict.fromkeys((*personal, *team)))
    if not base_url or not account or not personal or not team:
        raise typer.BadParameter(
            "base URL, account, personal and team scopes are required"
        )
    repositories: dict[str, object] = {}
    for scope in scopes:
        repository = _ask(f"Repository identity for {scope}", scope)
        repository_path = _ask(f"Repository path for {scope}", ".")
        branch = _ask(f"Target branch for {scope}", "main")
        tests = [
            x.strip()
            for x in _ask(f"Test commands for {scope} (semicolon separated)").split(";")
            if x.strip()
        ]
        if not tests:
            raise typer.BadParameter("at least one test command is required")
        repositories[scope] = {
            "repository": repository,
            "path": repository_path,
            "targetBranch": branch,
            "testCommands": tests,
        }
    payload = {
        "configVersion": 1,
        "zentao": {"baseUrl": base_url, "account": account},
        "personal": {"scopeNames": list(personal)},
        "team": {"scopeNames": list(team), "members": members},
        "repositories": repositories,
        "permissions": {
            "codeWriteEnabled": False,
            "commentEnabled": False,
            "stepUpdateEnabled": False,
        },
    }
    AppConfig.model_validate(payload)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
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
        if force:
            os.replace(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except FileExistsError:
                if json_output:
                    typer.echo(
                        json.dumps(
                            failure(2, "input", "configuration already exists", "path")
                        )
                    )
                else:
                    typer.echo("Configuration already exists", err=True)
                raise typer.Exit(2) from None
            os.unlink(temporary)
        emit(
            {"initialized": True, "configVersion": 1},
            json_output,
            label="Configuration initialized",
        )
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
