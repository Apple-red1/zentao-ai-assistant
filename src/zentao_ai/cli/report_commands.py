from __future__ import annotations

from pathlib import Path

import typer

from zentao_ai.workflows import run_personal, run_team_report

from .bug_commands import _emit
from .runtime import DependencyFactory, get_runtime, guarded

app = typer.Typer(help="Generate reports.")


@app.command("personal")
@guarded
def personal(ctx: typer.Context, project: Path = typer.Option(Path.cwd()), json_output: bool = typer.Option(False, "--json")) -> None:
    runtime = get_runtime(ctx.obj if isinstance(ctx.obj, DependencyFactory) else None, project)
    result = run_personal(runtime.context())
    _emit(result.to_v2_payload(), json_output)
    if result.completeness != "COMPLETE":
        raise typer.Exit(3)


@app.command("team")
@guarded
def team(ctx: typer.Context, project: Path = typer.Option(Path.cwd()), json_output: bool = typer.Option(False, "--json")) -> None:
    runtime = get_runtime(ctx.obj if isinstance(ctx.obj, DependencyFactory) else None, project)
    result = run_team_report(runtime.context())
    _emit(result.to_v2_payload(), json_output)
    if result.completeness != "COMPLETE":
        raise typer.Exit(3)
