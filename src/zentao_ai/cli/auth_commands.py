from __future__ import annotations

import typer
from pydantic import SecretStr

from zentao_ai.credentials.store import CredentialName

from .runtime import emit, failure, get_factory

app = typer.Typer(help="Manage credentials.")


@app.command("login")
def login(
    ctx: typer.Context,
    kind: CredentialName = typer.Option(CredentialName.API_TOKEN, "--kind"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Store a credential read from a hidden prompt."""
    try:
        value = typer.prompt("Credential", hide_input=True, confirmation_prompt=False)
    except (KeyboardInterrupt, typer.Abort):
        if json_output:
            import json

            typer.echo(json.dumps(failure(130, "cancelled", "operation cancelled")))
        raise typer.Exit(130) from None
    if not value.strip():
        if json_output:
            import json

            typer.echo(
                json.dumps(failure(2, "input", "credential is empty", "credential"))
            )
        else:
            typer.echo("Credential was not stored", err=True)
        raise typer.Exit(2)
    get_factory(ctx.obj).credential_store().set(kind, SecretStr(value))
    emit(
        {"credential": kind.value, "stored": True},
        json_output,
        label="Credential stored",
    )
