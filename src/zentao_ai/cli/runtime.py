from __future__ import annotations

import functools
import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from zentao_ai.config.loader import load_config
from zentao_ai.config.models import AppConfig
from zentao_ai.credentials.environment import CredentialUnavailableError, resolve_credential
from zentao_ai.credentials.store import CredentialName, CredentialStore
from zentao_ai.repository.guard import (
    GuardResult,
    RepositoryMapping,
    preflight_repository,
    verify_repository_unchanged,
)
from zentao_ai.state.ledger import Ledger
from zentao_ai.workflows.models import PatchOutcome, RunContext
from zentao_ai.zentao.http_provider import HttpZentaoProvider
from zentao_ai.zentao.models import ZentaoAuth, ZentaoEndpoints


def success(data: Any) -> dict[str, Any]:
    return {"ok": True, "code": 0, "data": data, "error": None}


def failure(
    code: int, kind: str, message: str, field_name: str | None = None
) -> dict[str, Any]:
    error = {"type": kind, "message": message}
    if field_name:
        error["field"] = field_name
    return {"ok": False, "code": code, "data": None, "error": error}


def emit(payload: Any, json_output: bool, *, label: str = "Result") -> None:
    if json_output:
        typer.echo(json.dumps(success(payload), ensure_ascii=False, default=str))
    else:
        typer.echo(f"{label}: {payload}")


@dataclass
class AppRuntime:
    config: AppConfig
    provider: Any
    ledger: Any
    clock: Callable[[], datetime]
    owner: str
    repository: Any = None
    patch_executor: Any = None
    report_sink: Any = None
    store: Any = None
    _closers: list[Callable[[], Any]] = field(default_factory=list, repr=False)

    def context(self, **overrides: Any) -> RunContext:
        values: dict[str, Any] = {
            "config": self.config,
            "provider": self.provider,
            "ledger": self.ledger,
            "now": self.clock,
            "owner": self.owner,
            "repository": self.repository,
            "patchExecutor": self.patch_executor,
            "reportSink": self.report_sink,
        }
        values.update(overrides)
        return RunContext(**values)

    def close(self) -> None:
        while self._closers:
            try:
                self._closers.pop()()
            except Exception:
                pass

    def __enter__(self) -> AppRuntime:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


@dataclass(frozen=True)
class RunPlan:
    config: AppConfig
    operations: tuple[str, ...] = (
        "query_my_bugs",
        "query_bug_detail",
        "query_bug_history",
    )
    fields: tuple[str, ...] = ("scopeNames", "page", "pageSize", "bugId")


class RepositoryAdapter:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def preflight(self, config: AppConfig, routing: Any) -> GuardResult:
        selected = routing.selected_repository
        matches = [
            (key, value)
            for key, value in config.repositories.items()
            if value.repository == selected
        ]
        if len(matches) != 1:
            raise ValueError("repository mapping is not unique")
        key, item = matches[0]
        path = Path(item.path)
        if not path.is_absolute():
            path = self.config_path.parent / path
        return preflight_repository(
            RepositoryMapping(
                repository=item.repository,
                path=path,
                targetBranch=item.targetBranch,
                testCommands=tuple(item.testCommands),
                configPath=self.config_path,
                repositoryKey=key,
            )
        )

    def unchanged(self, lease: GuardResult) -> bool:
        return verify_repository_unchanged(lease).unchanged


class LocalPatchExecutor:
    """Local-only patch port: runs configured tests and never commits/pushes."""

    def reproduce(self, repository: GuardResult, _bug: object) -> bool:
        if not repository.testCommands:
            return True
        return (
            subprocess.run(
                repository.testCommands[0], cwd=repository.path, shell=True, check=False
            ).returncode
            == 0
        )

    def apply(self, _repository: object, _bug: object) -> PatchOutcome:
        return PatchOutcome.FAILED  # no autonomous patch generator is configured

    def test(self, repository: GuardResult, commands: Any) -> bool:
        return all(
            subprocess.run(
                command, cwd=repository.path, shell=True, check=False
            ).returncode
            == 0
            for command in commands
        )

    def diff_safe(self, repository: GuardResult) -> bool:
        return verify_repository_unchanged(repository).unchanged


class JsonReportSink:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def write(self, payload: dict[str, object]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / f"{payload.get('businessDate', 'report')}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, target)


class DependencyFactory:
    def __init__(
        self,
        builder: Callable[[Path], AppRuntime] | None = None,
        *,
        credential_builder: Callable[[], Any] | None = None,
        plan_builder: Callable[[Path], RunPlan] | None = None,
    ) -> None:
        self._builder = builder or self._production
        self._credential_builder = credential_builder or CredentialStore
        self._plan_builder = plan_builder or self._production_plan

    def __call__(self, project: Path) -> AppRuntime:
        return self._builder(project.resolve())

    def credential_store(self) -> Any:
        return self._credential_builder()

    def plan(self, project: Path) -> RunPlan:
        return self._plan_builder(project.resolve())

    @staticmethod
    def _production_plan(project: Path) -> RunPlan:
        return RunPlan(load_config(project / ".codex" / "zentao-ai-bug.yaml"))

    @staticmethod
    def _production(project: Path) -> AppRuntime:
        config_path = project / ".codex" / "zentao-ai-bug.yaml"
        config = load_config(config_path)
        store = CredentialStore()
        try:
            token = resolve_credential(CredentialName.API_TOKEN, os.environ, store)
            password = None
        except CredentialUnavailableError:
            token = None
            password = resolve_credential(CredentialName.PASSWORD, os.environ, store)
        if not config.zentao.baseUrl:
            raise ValueError("zentao.baseUrl is required")
        provider = HttpZentaoProvider(
            base_url=config.zentao.baseUrl,
            endpoints=ZentaoEndpoints(
                login="/api.php/v2/users/login",
                myBugs="/api/bugs/mine",
                userBugs="/api.php/v2/bugs",
                bugDetail="/api.php/v2/bugs/{bug_id}",
                bugHistory="/api.php/v2/bugs/{bug_id}",
                statistics="/api/bugs/statistics",
                addComment="/api/bugs/{bug_id}/comments",
                updateSteps="/api/bugs/{bug_id}/steps",
            ),
            auth=ZentaoAuth(
                username=config.zentao.account, apiToken=token, password=password, webCookie=None
            ),
        )
        ledger = Ledger(project / ".codex" / "zentao-ai-state.sqlite3")
        ledger.__enter__()
        report_dir = Path(config.reporting.outputDirectory)
        if not report_dir.is_absolute():
            report_dir = project / report_dir
        return AppRuntime(
            config,
            provider,
            ledger,
            datetime.now,
            f"cli-{os.getpid()}",
            RepositoryAdapter(config_path),
            LocalPatchExecutor(),
            JsonReportSink(report_dir),
            store,
            [provider.close, lambda: ledger.__exit__(None, None, None)],
        )


def get_factory(value: object) -> DependencyFactory:
    return value if isinstance(value, DependencyFactory) else DependencyFactory()


def guarded(function: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(function)
    def invoke(*args: Any, **kwargs: Any) -> Any:
        json_output = bool(kwargs.get("json_output", False))
        try:
            return function(*args, **kwargs)
        except (KeyboardInterrupt, typer.Abort):
            if json_output:
                typer.echo(json.dumps(failure(130, "cancelled", "operation cancelled")))
            raise typer.Exit(130) from None
        except typer.Exit:
            raise
        except (ValueError, FileNotFoundError, typer.BadParameter) as exc:
            if json_output:
                typer.echo(json.dumps(failure(2, "input", type(exc).__name__)))
            else:
                typer.echo(f"Input/configuration error: {type(exc).__name__}", err=True)
            raise typer.Exit(2) from None
        except Exception as exc:
            if json_output:
                typer.echo(json.dumps(failure(3, "business", type(exc).__name__)))
            else:
                typer.echo(f"Operation failed: {type(exc).__name__}", err=True)
            raise typer.Exit(3) from None

    return invoke
