from __future__ import annotations

import json
from pathlib import Path

import typer

from zentao_ai.workflows import run_personal

from .auth_commands import app as auth_app
from .bug_commands import bug_app, bugs_app, repair_command
from .config_commands import app as config_app
from .doctor import doctor_command
from .report_commands import app as report_app
from .runtime import emit, get_factory, guarded

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
    if dry_run:
        plan = get_factory(ctx.obj).plan(project)
        payload = {
            "status": "仅计划、未执行",
            "executed": False,
            "operations": list(plan.operations),
            "fields": list(plan.fields),
            "scopeNames": list(plan.config.personal.scopeNames),
        }
        emit(payload, json_output, label="Plan (not executed)")
        return
    with get_factory(ctx.obj)(project) as runtime:
        from .bug_commands import _placeholder, _request

        request = _request(runtime, _placeholder())
        result = run_personal(runtime.context(config=request.config))
        emit(result.to_v2_payload(), json_output)
        if result.completeness != "COMPLETE":
            raise typer.Exit(3)


@mcp_app.command("serve")
def mcp_serve(json_output: bool = typer.Option(False, "--json")) -> None:
    """Delegate to the MCP server supplied by the next delivery task."""
    if json_output:
        from .runtime import failure

        typer.echo(
            json.dumps(
                failure(2, "unavailable", "MCP server delegation is not installed")
            )
        )
    else:
        typer.echo("MCP server delegation is not installed", err=True)
    raise typer.Exit(2)


app.add_typer(mcp_app, name="mcp")


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
