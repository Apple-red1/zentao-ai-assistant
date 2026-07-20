from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import typer

from .runtime import failure, get_factory, success


def doctor_command(
    ctx: typer.Context,
    project: Path = typer.Option(Path.cwd(), "--project"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    checks: list[dict[str, Any]] = []

    def check(name: str, operation: Any, *, required: bool = True) -> None:
        try:
            detail = operation()
            checks.append(
                {
                    "name": name,
                    "status": "PASS",
                    "required": required,
                    "detail": str(detail) if detail else "ok",
                }
            )
        except Exception as exc:
            checks.append(
                {
                    "name": name,
                    "status": "FAIL",
                    "required": required,
                    "detail": type(exc).__name__,
                }
            )

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

    box: list[Any] = []
    check("config", lambda: box.append(get_factory(ctx.obj)(project)))
    runtime = box[0] if box else None

    query_probe_box: list[Any] = []

    def query_probe() -> Any:
        if runtime is None:
            raise RuntimeError("runtime unavailable")
        if not query_probe_box:
            query_probe_box.append(
                runtime.provider.query_my_bugs(
                    scope_names=tuple(runtime.config.personal.scopeNames),
                    page=1,
                    page_size=1,
                )
            )
        return query_probe_box[0]

    check(
        "credentials",
        lambda: (query_probe(), "query authentication accepted")[1],
    )
    check(
        "connection",
        lambda: (query_probe(), "bug query endpoint reachable")[1],
    )
    check(
        "query-permission",
        query_probe,
    )
    check(
        "repository",
        lambda: (
            subprocess.run(
                ["git", "-C", str(project), "rev-parse", "--show-toplevel"],
                check=True,
                capture_output=True,
                text=True,
            ),
            "repository available",
        )[1],
    )
    check(
        "branch",
        lambda: subprocess.run(
            ["git", "-C", str(project), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
    )
    check(
        "tests",
        lambda: require(
            runtime
            and all(
                item.testCommands
                and all(command.strip() for command in item.testCommands)
                for item in runtime.config.repositories.values()
            )
        ),
    )
    check(
        "mcp-executable",
        lambda: (
            shutil.which("zentao-ai")
            or shutil.which("python")
            or (_ for _ in ()).throw(RuntimeError())
        ),
    )
    check("report-directory", lambda: require(report_writable(runtime)))
    failed = any(item["required"] and item["status"] == "FAIL" for item in checks)
    if json_output:
        envelope = (
            success({"checks": checks})
            if not failed
            else failure(2, "doctor", "required check failed")
        )
        if failed:
            envelope["data"] = {"checks": checks}
        typer.echo(json.dumps(envelope, ensure_ascii=False))
    else:
        for item in checks:
            typer.echo(f"{item['status']} {item['name']}: {item['detail']}")
    if runtime is not None:
        runtime.close()
    if failed:
        raise typer.Exit(2)
