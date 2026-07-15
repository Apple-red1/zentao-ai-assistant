from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import typer

from zentao_ai.credentials.store import CredentialName

from .runtime import DependencyFactory, get_runtime


def doctor_command(
    ctx: typer.Context,
    project: Path = typer.Option(Path.cwd(), "--project"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    checks: list[dict[str, Any]] = []

    def check(name: str, operation: Any, *, required: bool = True) -> None:
        try:
            detail = operation()
            checks.append({"name": name, "status": "PASS", "required": required, "detail": str(detail) if detail else "ok"})
        except Exception as exc:
            checks.append({"name": name, "status": "FAIL", "required": required, "detail": type(exc).__name__})

    def require(value: Any) -> Any:
        if value is None or value is False:
            raise RuntimeError("check failed")
        return value

    def report_writable(runtime_value: Any) -> bool:
        if runtime_value is None:
            return False
        output = project / runtime_value.config.reporting.outputDirectory
        target = output if output.exists() else output.parent
        return os.access(target, os.W_OK)

    factory = ctx.obj if isinstance(ctx.obj, DependencyFactory) else None
    box: list[Any] = []
    check("config", lambda: box.append(get_runtime(factory, project)))
    runtime = box[0] if box else None
    check("credentials", lambda: require(runtime.store.get(CredentialName.API_TOKEN)) if runtime and runtime.store else require(None))
    check("connection", lambda: runtime.provider.bug_statistics() if runtime else (_ for _ in ()).throw(RuntimeError()))
    check("query-permission", lambda: runtime.provider.query_my_bugs(scope_names=tuple(runtime.config.personal.scopeNames), page=1, page_size=1) if runtime else (_ for _ in ()).throw(RuntimeError()))
    check("repository", lambda: subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip())
    check("branch", lambda: subprocess.run(["git", "-C", str(project), "branch", "--show-current"], check=True, capture_output=True, text=True).stdout.strip())
    check("tests", lambda: require(runtime and all(item.testCommands and all(command.strip() for command in item.testCommands) for item in runtime.config.repositories.values())))
    check("mcp-executable", lambda: shutil.which("zentao-ai") or shutil.which("python") or (_ for _ in ()).throw(RuntimeError()))
    check("report-directory", lambda: require(report_writable(runtime)))
    failed = any(item["required"] and item["status"] == "FAIL" for item in checks)
    if json_output:
        typer.echo(json.dumps({"ok": not failed, "checks": checks}, ensure_ascii=False))
    else:
        for item in checks:
            typer.echo(f'{item["status"]} {item["name"]}: {item["detail"]}')
    if failed:
        raise typer.Exit(2)
