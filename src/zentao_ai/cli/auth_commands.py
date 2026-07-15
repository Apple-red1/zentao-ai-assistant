from __future__ import annotations

from pathlib import Path

import typer
from pydantic import SecretStr

from zentao_ai.credentials.store import CredentialName, CredentialStore

from .runtime import DependencyFactory, get_runtime

app = typer.Typer(help="Manage credentials.")


@app.command("login")
def login(
    ctx: typer.Context,
    project: Path = typer.Option(Path.cwd(), "--project"),
    kind: CredentialName = typer.Option(CredentialName.API_TOKEN, "--kind"),
) -> None:
    """Store a credential read from a hidden prompt."""
    try:
        value = typer.prompt("Credential", hide_input=True, confirmation_prompt=False)
    except (KeyboardInterrupt, typer.Abort):
        raise typer.Exit(130) from None
    if not value.strip():
        typer.echo("credential was not stored", err=True)
        raise typer.Exit(2)
    factory = ctx.obj if isinstance(ctx.obj, DependencyFactory) else None
    store = get_runtime(factory, project).store or CredentialStore()
    store.set(kind, SecretStr(value))
    typer.echo("credential stored")
