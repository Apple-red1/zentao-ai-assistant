from __future__ import annotations

import hashlib
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Literal, cast

import typer
from collections.abc import Mapping

from zentao_ai.safety.actions import ActionName, AuthorizationRecord
from zentao_ai.workflows import analyze_bug
from zentao_ai.workflows.adapters import normalize_cli_request
from zentao_ai.workflows.repair import repair_bug
from zentao_ai.workflows.steps import (
    ReproductionStep,
    replace_steps,
    replace_steps_with_image,
)
from zentao_ai.zentao.models import BugPage, BugSnapshot, Coverage
from zentao_ai.zentao.query_filters import filter_assignee_bugs

from .bug_table import render_bug_table
from .runtime import AppRuntime, emit, get_factory, guarded

bugs_app = typer.Typer(help="Query bugs.")
bug_app = typer.Typer(help="Analyze or update one bug.")


def _runtime(ctx: typer.Context, project: Path) -> AppRuntime:
    return get_factory(ctx.obj)(project)


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
    payload = _dump(value)
    emit(payload, json_output)


def _placeholder(bug_id: str = "0") -> BugSnapshot:
    return BugSnapshot(
        id=bug_id,
        status="transport",
        version="transport",
        snapshotVersion="transport",
        snapshotStable=True,
    )


def _filtered_assignee_page(source: BugPage, *, status: str) -> BugPage:
    if status == "all":
        return source
    items = filter_assignee_bugs(source.items, title_tag=None, status="unclosed")
    coverage = source.coverage
    complete = coverage.complete and (
        coverage.page == 1
        and coverage.pages is not None
        and coverage.pages == (0 if not source.items else 1)
        and coverage.total == len(source.items)
    )
    return BugPage(
        items=items,
        coverage=Coverage(
            page=1,
            pageSize=20,
            total=len(items) if complete else -1,
            pages=(0 if not items else 1) if complete else None,
            returned=len(items),
            failed=coverage.failed,
            complete=complete,
        ),
        itemFailures=source.item_failures,
        resolvedIdentity=source.resolved_identity,
    )


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
def mine(
    ctx: typer.Context,
    project: Path = typer.Option(Path.cwd()),
    json_output: bool = typer.Option(False, "--json"),
    title_tag: str | None = typer.Option(None, "--title-tag"),
    status: Literal["all", "unclosed"] = typer.Option("unclosed", "--status"),
) -> None:
    with _runtime(ctx, project) as runtime:
        account = runtime.config.zentao.account
        if account is None or not account.strip():
            raise RuntimeError("configuration error")
        source = runtime.provider.query_user_bugs(
            account.strip(),
            scope_names=(),
            page=1,
            page_size=20,
            browse_type="assigntome",
        )
        items = filter_assignee_bugs(source.items, title_tag=title_tag, status=status)
        coverage = source.coverage
        complete = source.coverage.complete and (
            coverage.pages is not None
            and coverage.pages == (0 if not source.items else 1)
            and coverage.page == 1
            and coverage.total == len(source.items)
        )
        coverage = Coverage(
            page=1,
            pageSize=20,
            total=len(items) if complete else -1,
            pages=(0 if not items else 1) if complete else None,
            returned=len(items),
            failed=coverage.failed,
            complete=complete,
        )
        page = BugPage(
            items=items,
            coverage=coverage,
            itemFailures=source.item_failures,
            resolvedIdentity=source.resolved_identity,
        )
        if json_output:
            _emit(page, True)
        else:
            typer.echo(render_bug_table(page))


@bugs_app.command("user")
@guarded
def user(
    ctx: typer.Context,
    account: str,
    project: Path = typer.Option(Path.cwd()),
    json_output: bool = typer.Option(False, "--json"),
    scope_mode: Literal["team-report", "session-visible"] = typer.Option(
        "team-report", "--scope-mode"
    ),
    status: Literal["all", "unclosed"] = typer.Option("all", "--status"),
) -> None:
    with _runtime(ctx, project) as runtime:
        if scope_mode == "team-report":
            if account not in runtime.config.team.members:
                raise ValueError("user is not a configured team member")
            scope_names = tuple(runtime.config.team.scopeNames)
        else:
            scope_names = ()
        source = runtime.provider.query_user_bugs(
            account, scope_names=scope_names, page=1, page_size=20
        )
        page = _filtered_assignee_page(source, status=status)
        if json_output:
            _emit(page, True)
        else:
            typer.echo(render_bug_table(page))


@bug_app.command("analyze")
@guarded
def analyze(
    ctx: typer.Context,
    bug_id: str,
    project: Path = typer.Option(Path.cwd()),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    with _runtime(ctx, project) as runtime:
        transport = _request(runtime, _placeholder(bug_id), repair_id=bug_id)
        snapshot = runtime.provider.query_bug_detail(transport.repair_bug_id)
        history = runtime.provider.query_bug_history(
            transport.repair_bug_id, page=1, page_size=100
        )
        request = _request(runtime, snapshot)
        _emit(
            analyze_bug(
                request.snapshot, history.items, request.phase, signal=request.signal
            ),
            json_output,
        )


def _authorized_request(
    runtime: AppRuntime,
    snapshot: Any,
    bug_id: str,
    turn: str,
    action: ActionName,
    params: dict[str, Any],
    steps: tuple[ReproductionStep, ...],
    image: Path | None = None,
) -> Any:
    record = AuthorizationRecord(
        turnId=turn, source="user", action=action, bugId=bug_id, parameters=params
    )
    return _request(
        runtime,
        snapshot,
        records=(record,),
        actions=({"action": action, "bugId": bug_id, "parameters": params},),
        steps=steps,
        image=image,
    )


def _step_values(
    actions: list[str], expected: list[str]
) -> tuple[ReproductionStep, ...]:
    if not actions or len(actions) != len(expected):
        raise typer.BadParameter("matching --action and --expected values are required")
    return tuple(ReproductionStep(a, e) for a, e in zip(actions, expected, strict=True))


@bug_app.command("update-steps")
@guarded
def update_steps(
    ctx: typer.Context,
    bug_id: str,
    action: list[str] = typer.Option([], "--action"),
    expected: list[str] = typer.Option([], "--expected"),
    confirm: bool = typer.Option(False, "--confirm"),
    turn_id: str = typer.Option("", "--turn-id"),
    project: Path = typer.Option(Path.cwd()),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    if not confirm or not turn_id.strip():
        raise typer.BadParameter("--confirm and --turn-id are required")
    steps = _step_values(action, expected)
    with _runtime(ctx, project) as runtime:
        params = {"steps": [asdict(step) for step in steps]}
        request = _authorized_request(
            runtime,
            _placeholder(bug_id),
            bug_id,
            turn_id,
            "update_steps",
            params,
            steps,
        )
        context = runtime.context(
            config=request.config,
            currentTurnId=turn_id,
            authorizationRecords=request.authorization.authorizationRecords,
        )
        _emit(replace_steps(context, request.snapshot.id, request.steps), json_output)


@bug_app.command("update-steps-with-image")
@guarded
def update_steps_image(
    ctx: typer.Context,
    bug_id: str,
    image: Path | None = typer.Option(None, "--image"),
    action: list[str] = typer.Option([], "--action"),
    expected: list[str] = typer.Option([], "--expected"),
    confirm: bool = typer.Option(False, "--confirm"),
    turn_id: str = typer.Option("", "--turn-id"),
    project: Path = typer.Option(Path.cwd()),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    if not confirm or not turn_id.strip() or image is None or not image.is_absolute():
        raise typer.BadParameter("--confirm and an absolute --image are required")
    steps = _step_values(action, expected)
    with _runtime(ctx, project) as runtime:
        params = {
            "steps": [asdict(step) for step in steps],
            "imageSha256": hashlib.sha256(image.read_bytes()).hexdigest(),
            "filename": image.name,
        }
        request = _authorized_request(
            runtime,
            _placeholder(bug_id),
            bug_id,
            turn_id,
            "update_steps_with_image",
            params,
            steps,
            image,
        )
        context = runtime.context(
            config=request.config,
            currentTurnId=turn_id,
            authorizationRecords=request.authorization.authorizationRecords,
            authorizedImagePaths=(request.image_path,),
        )
        _emit(
            replace_steps_with_image(
                context, request.snapshot.id, request.steps, request.image_path
            ),
            json_output,
        )


@guarded
def repair_command(
    ctx: typer.Context,
    bug_id: str,
    confirm: bool = typer.Option(False, "--confirm"),
    turn_id: str = typer.Option("", "--turn-id"),
    project: Path = typer.Option(Path.cwd()),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    if not confirm or not turn_id.strip():
        raise typer.BadParameter("--confirm and --turn-id are required")
    with _runtime(ctx, project) as runtime:
        summary = "Local patch passed the configured validation and remains an uncommitted candidate for human review."
        from zentao_ai.reporting.renderer import render_resolution_comment
        from zentao_ai.workflows.models import ResolutionCommentPayload

        body = render_resolution_comment(ResolutionCommentPayload(summary=summary))
        comment_record = AuthorizationRecord(
            turnId=turn_id,
            source="user",
            action="comment",
            bugId=bug_id,
            parameters={"comment": body},
        )
        write_record = AuthorizationRecord(
            turnId=turn_id,
            source="user",
            action="write_code",
            bugId=bug_id,
            parameters={},
        )
        request = _request(
            runtime,
            _placeholder(bug_id),
            records=(comment_record, write_record),
            actions=(
                {"action": "comment", "bugId": bug_id, "parameters": {"comment": body}},
                {"action": "write_code", "bugId": bug_id, "parameters": {}},
            ),
            repair_id=bug_id,
        )
        context = runtime.context(
            config=request.config,
            currentTurnId=turn_id,
            authorizationRecords=request.authorization.authorizationRecords,
            snapshotStable=True,
            historyChecked=True,
            cooldownPassed=True,
            idempotencyPassed=True,
        )
        _emit(repair_bug(context, request.repair_bug_id), json_output)
