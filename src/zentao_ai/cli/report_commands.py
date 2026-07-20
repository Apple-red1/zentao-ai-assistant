from __future__ import annotations

from pathlib import Path

import typer

from zentao_ai.workflows import run_personal, run_team_report

from .bug_commands import _emit, _placeholder, _request
from .runtime import get_factory, guarded

app = typer.Typer(help="Generate reports.")


@app.command("personal")
@guarded
def personal(
    ctx: typer.Context,
    project: Path = typer.Option(Path.cwd()),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    with get_factory(ctx.obj)(project) as runtime:
        request = _request(runtime, _placeholder())
        result = run_personal(runtime.context(config=request.config))
        _emit(result.to_v2_payload(), json_output)


@app.command("team")
@guarded
def team(
    ctx: typer.Context,
    project: Path = typer.Option(Path.cwd()),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    with get_factory(ctx.obj)(project) as runtime:
        request = _request(runtime, _placeholder())
        result = run_team_report(runtime.context(config=request.config))
        _emit(result.to_v2_payload(), json_output)
