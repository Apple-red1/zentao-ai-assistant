from __future__ import annotations

import functools
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from zentao_ai.config.loader import load_config
from zentao_ai.config.models import AppConfig
from zentao_ai.credentials.environment import resolve_credential
from zentao_ai.credentials.store import CredentialName, CredentialStore
from zentao_ai.state.ledger import Ledger
from zentao_ai.workflows.models import RunContext
from zentao_ai.zentao.http_provider import HttpZentaoProvider
from zentao_ai.zentao.models import ZentaoAuth, ZentaoEndpoints


@dataclass(frozen=True)
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


class DependencyFactory:
    """Single injectable boundary for CLI dependencies."""

    def __init__(self, builder: Callable[[Path], AppRuntime] | None = None) -> None:
        self._builder = builder or self._production

    def __call__(self, project: Path) -> AppRuntime:
        return self._builder(project.resolve())

    @staticmethod
    def _production(project: Path) -> AppRuntime:
        config_path = project / ".codex" / "zentao-ai-bug.yaml"
        config = load_config(config_path)
        store = CredentialStore()
        token = resolve_credential(CredentialName.API_TOKEN, os.environ, store)
        if not config.zentao.baseUrl:
            raise ValueError("zentao.baseUrl is required")
        provider = HttpZentaoProvider(
            base_url=config.zentao.baseUrl,
            endpoints=ZentaoEndpoints(
                myBugs="/api/bugs/mine",
                userBugs="/api/bugs/user/{user}",
                bugDetail="/api/bugs/{bug_id}",
                bugHistory="/api/bugs/{bug_id}/history",
                statistics="/api/bugs/statistics",
                addComment="/api/bugs/{bug_id}/comments",
                updateSteps="/api/bugs/{bug_id}/steps",
            ),
            auth=ZentaoAuth(
                username=config.zentao.account, apiToken=token, webCookie=None
            ),
        )
        ledger = Ledger(project / ".codex" / "zentao-ai-state.sqlite3")
        ledger.__enter__()
        return AppRuntime(
            config,
            provider,
            ledger,
            datetime.now,
            f"cli-{os.getpid()}",
            store=store,
        )


def get_runtime(factory: DependencyFactory | None, project: Path) -> AppRuntime:
    return (factory or DependencyFactory())(project)


def guarded(function: Callable[..., Any]) -> Callable[..., Any]:
    """Map failures to stable exit codes without exposing exception text."""
    @functools.wraps(function)
    def invoke(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except (KeyboardInterrupt, typer.Abort):
            raise typer.Exit(130) from None
        except (ValueError, FileNotFoundError) as exc:
            typer.echo(f"input/configuration error ({type(exc).__name__})", err=True)
            raise typer.Exit(2) from None
        except typer.Exit:
            raise
        except Exception as exc:
            typer.echo(f"operation failed ({type(exc).__name__})", err=True)
            raise typer.Exit(3) from None
    return invoke
