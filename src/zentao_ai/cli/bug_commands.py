from __future__ import annotations

import hashlib
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, cast

import typer
from collections.abc import Mapping

from zentao_ai.safety.actions import ActionName, AuthorizationRecord
from zentao_ai.workflows import analyze_bug
from zentao_ai.workflows.adapters import normalize_cli_request
from zentao_ai.workflows.repair import repair_bug
from zentao_ai.workflows.steps import ReproductionStep, replace_steps, replace_steps_with_image

from .runtime import AppRuntime, DependencyFactory, get_runtime, guarded

bugs_app = typer.Typer(help="Query bugs.")
bug_app = typer.Typer(help="Analyze or update one bug.")


def _runtime(ctx: typer.Context, project: Path) -> AppRuntime:
    return get_runtime(ctx.obj if isinstance(ctx.obj, DependencyFactory) else None, project)


def _dump(value: Any) -> Any:
    fields = getattr(type(value), "model_fields", None)
    if fields is not None:
        return {
            (field.alias or name): _dump(getattr(value, name))
            for name, field in fields.items()
        }
    if is_dataclass(value):
        return asdict(cast(Any, value))
    return _thaw(value)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _dump(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_dump(item) for item in value]
    return value


def _emit(value: Any, json_output: bool) -> None:
    import json
    payload = _dump(value)
    typer.echo(json.dumps(payload, ensure_ascii=False, default=str) if json_output else str(payload))


def _request(
    runtime: AppRuntime,
    snapshot: Any,
    *,
    records: tuple[AuthorizationRecord, ...] = (),
    actions: tuple[dict[str, Any], ...] = (),
    steps: tuple[ReproductionStep, ...] = (),
    image: Path | None = None,
    repair_id: str = "",
) -> Any:
    return normalize_cli_request(
        {
            "config": runtime.config.model_dump(),
            "snapshot": _dump(snapshot),
            "phase": "FINAL_DECISION",
            "signal": {},
            "authorization": {
                "context": {"currentTurnId": records[0].turnId if records else None},
                "records": [record.model_dump() for record in records],
            },
            "actions": list(actions),
            "steps": [asdict(step) for step in steps],
            "imagePath": str(image or Path.cwd()),
            "repairBugId": repair_id,
        }
    )


@bugs_app.command("mine")
@guarded
def mine(ctx: typer.Context, project: Path = typer.Option(Path.cwd()), json_output: bool = typer.Option(False, "--json")) -> None:
    runtime = _runtime(ctx, project)
    page = runtime.provider.query_my_bugs(scope_names=tuple(runtime.config.personal.scopeNames), page=1, page_size=20)
    if page.items:
        request = _request(runtime, page.items[0])
        assert request.scope_names == tuple(runtime.config.personal.scopeNames)
    _emit(page, json_output)


@bugs_app.command("user")
@guarded
def user(ctx: typer.Context, account: str, project: Path = typer.Option(Path.cwd()), json_output: bool = typer.Option(False, "--json")) -> None:
    runtime = _runtime(ctx, project)
    page = runtime.provider.query_user_bugs(account, scope_names=tuple(runtime.config.personal.scopeNames), page=1, page_size=20)
    if page.items:
        _request(runtime, page.items[0])
    _emit(page, json_output)


@bug_app.command("analyze")
@guarded
def analyze(ctx: typer.Context, bug_id: str, project: Path = typer.Option(Path.cwd()), json_output: bool = typer.Option(False, "--json")) -> None:
    runtime = _runtime(ctx, project)
    snapshot = runtime.provider.query_bug_detail(bug_id)
    history = runtime.provider.query_bug_history(bug_id, page=1, page_size=100)
    request = _request(runtime, snapshot)
    result = analyze_bug(request.snapshot, history.items, request.phase, signal=request.signal)
    _emit(result, json_output)


def _authorized_request(runtime: AppRuntime, snapshot: Any, bug_id: str, turn: str, action: ActionName, params: dict[str, Any], steps: tuple[ReproductionStep, ...], image: Path | None = None) -> Any:
    record = AuthorizationRecord(turnId=turn, source="user", action=action, bugId=bug_id, parameters=params)
    return _request(runtime, snapshot, records=(record,), actions=({"action": action, "bugId": bug_id, "parameters": params},), steps=steps, image=image)


def _step_values(actions: list[str], expected: list[str]) -> tuple[ReproductionStep, ...]:
    if not actions or len(actions) != len(expected):
        raise typer.BadParameter("matching --action and --expected values are required")
    return tuple(ReproductionStep(a, e) for a, e in zip(actions, expected, strict=True))


@bug_app.command("update-steps")
@guarded
def update_steps(ctx: typer.Context, bug_id: str, action: list[str] = typer.Option(..., "--action"), expected: list[str] = typer.Option(..., "--expected"), confirm: bool = typer.Option(False, "--confirm"), turn_id: str = typer.Option(..., "--turn-id"), project: Path = typer.Option(Path.cwd()), json_output: bool = typer.Option(False, "--json")) -> None:
    if not confirm:
        raise typer.BadParameter("--confirm is required")
    runtime, steps = _runtime(ctx, project), _step_values(action, expected)
    snapshot = runtime.provider.query_bug_detail(bug_id)
    params = {"steps": [asdict(step) for step in steps]}
    request = _authorized_request(runtime, snapshot, bug_id, turn_id, "update_steps", params, steps)
    context = runtime.context(currentTurnId=turn_id, authorizationRecords=request.authorization.authorizationRecords)
    _emit(replace_steps(context, bug_id, request.steps), json_output)


@bug_app.command("update-steps-with-image")
@guarded
def update_steps_image(ctx: typer.Context, bug_id: str, image: Path = typer.Option(..., "--image"), action: list[str] = typer.Option(..., "--action"), expected: list[str] = typer.Option(..., "--expected"), confirm: bool = typer.Option(False, "--confirm"), turn_id: str = typer.Option(..., "--turn-id"), project: Path = typer.Option(Path.cwd()), json_output: bool = typer.Option(False, "--json")) -> None:
    if not confirm or not image.is_absolute():
        raise typer.BadParameter("--confirm and an absolute --image are required")
    runtime, steps = _runtime(ctx, project), _step_values(action, expected)
    snapshot = runtime.provider.query_bug_detail(bug_id)
    params = {"steps": [asdict(step) for step in steps], "imageSha256": hashlib.sha256(image.read_bytes()).hexdigest(), "filename": image.name}
    request = _authorized_request(runtime, snapshot, bug_id, turn_id, "update_steps_with_image", params, steps, image)
    context = runtime.context(currentTurnId=turn_id, authorizationRecords=request.authorization.authorizationRecords, authorizedImagePaths=(request.image_path,))
    _emit(replace_steps_with_image(context, bug_id, request.steps, request.image_path), json_output)


@guarded
def repair_command(ctx: typer.Context, bug_id: str, confirm: bool = typer.Option(False, "--confirm"), turn_id: str = typer.Option(..., "--turn-id"), project: Path = typer.Option(Path.cwd()), json_output: bool = typer.Option(False, "--json")) -> None:
    if not confirm:
        raise typer.BadParameter("--confirm is required")
    runtime = _runtime(ctx, project)
    snapshot = runtime.provider.query_bug_detail(bug_id)
    request = _request(runtime, snapshot, repair_id=bug_id)
    # Repair's shared workflow performs all safety and write authorization checks.
    _emit(repair_bug(runtime.context(currentTurnId=turn_id), request.repair_bug_id), json_output)
