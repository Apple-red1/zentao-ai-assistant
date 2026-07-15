from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from zentao_ai.workflows import run_personal

from .auth_commands import app as auth_app
from .bug_commands import bug_app, bugs_app, repair_command
from .config_commands import app as config_app
from .doctor import doctor_command
from .report_commands import app as report_app
from .runtime import DependencyFactory, get_runtime, guarded

app = typer.Typer(help="Safe standalone Zentao AI assistant.", no_args_is_help=True)
mcp_app = typer.Typer(help="MCP integration.")
app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")
app.add_typer(bugs_app, name="bugs")
app.add_typer(report_app, name="report")
app.add_typer(bug_app, name="bug")
app.command("doctor")(doctor_command)
app.command("repair")(repair_command)


@app.command("run")
@guarded
def run(
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run"),
    project: Path = typer.Option(Path.cwd(), "--project"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    runtime = get_runtime(ctx.obj if isinstance(ctx.obj, DependencyFactory) else None, project)
    if dry_run:
        payload: dict[str, Any] = {
            "status": "仅计划、未执行",
            "executed": False,
            "operations": ["query_my_bugs", "query_bug_detail", "query_bug_history"],
            "fields": ["scopeNames", "page", "pageSize", "bugId"],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False) if json_output else f'{payload["status"]}: ' + " -> ".join(payload["operations"]))
        return
    result = run_personal(runtime.context())
    typer.echo(json.dumps(result.to_v2_payload(), ensure_ascii=False, default=str) if json_output else str(result))
    if result.completeness != "COMPLETE":
        raise typer.Exit(3)


@mcp_app.command("serve")
def mcp_serve() -> None:
    """Delegate to the MCP server supplied by the next delivery task."""
    typer.echo("MCP server delegation is not installed", err=True)
    raise typer.Exit(2)


app.add_typer(mcp_app, name="mcp")


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
