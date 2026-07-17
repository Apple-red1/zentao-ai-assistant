from __future__ import annotations

import json
from pathlib import Path
from pydantic import SecretStr

from typer.testing import CliRunner

from zentao_ai.cli.app import app
from zentao_ai.cli.runtime import AppRuntime, DependencyFactory, RunPlan
from zentao_ai.config.models import AppConfig
from zentao_ai.config.loader import load_config
from zentao_ai.credentials.store import CredentialName
from zentao_ai.zentao.models import BugPage, BugSnapshot, Coverage


CONFIG = AppConfig.model_validate(
    {
        "configVersion": 1,
        "personal": {"scopeNames": ["demo"]},
        "team": {"scopeNames": ["demo"], "members": ["alice"]},
        "repositories": {
            "demo": {
                "repository": "demo",
                "path": ".",
                "targetBranch": "main",
                "testCommands": ["pytest"],
            }
        },
    }
)


class Store:
    def __init__(self) -> None:
        self.values: dict[CredentialName, str] = {}

    def set(self, name: CredentialName, value: object) -> None:
        self.values[name] = value.get_secret_value()  # type: ignore[attr-defined]

    def get(self, name: CredentialName) -> None:
        return None


class TokenOnlyStore(Store):
    def __init__(self) -> None:
        super().__init__()
        self.reads: list[CredentialName] = []

    def get(self, name: CredentialName) -> SecretStr | None:
        self.reads.append(name)
        if name is CredentialName.API_TOKEN:
            return SecretStr("doctor-token-secret")
        return None


class PasswordOnlyStore(Store):
    def get(self, name: CredentialName) -> SecretStr | None:
        if name is CredentialName.PASSWORD:
            return SecretStr("doctor-password-secret")
        return None


class Provider:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def query_my_bugs(
        self, *, scope_names: tuple[str, ...], page: int, page_size: int
    ) -> BugPage:
        self.calls.append(("mine", scope_names, page, page_size))
        bug = BugSnapshot(id=7, status="active", version="v1", snapshotVersion="v1")
        return BugPage(items=(bug,), coverage=Coverage(total=1))

    def bug_statistics(self) -> dict[str, int]:
        return {"active": 1}


def factory(
    tmp_path: Path, provider: Provider | None = None, store: Store | None = None
) -> DependencyFactory:
    runtime = AppRuntime(
        CONFIG,
        provider or Provider(),
        object(),
        lambda: None,
        "test",
        store=store or Store(),
    )
    selected = store or Store()
    return DependencyFactory(
        lambda _project: runtime,
        credential_builder=lambda: selected,
        plan_builder=lambda _project: RunPlan(CONFIG),
    )


def test_help_exposes_complete_command_tree() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in (
        "config",
        "auth",
        "doctor",
        "bugs",
        "report",
        "bug",
        "repair",
        "run",
        "mcp",
    ):
        assert command in result.stdout


def test_config_init_refuses_existing_then_force_replaces(tmp_path: Path) -> None:
    target = tmp_path / ".codex" / "zentao-ai-bug.yaml"
    target.parent.mkdir()
    target.write_text("old", encoding="utf-8")
    runner = CliRunner()
    answers = "https://zentao.example\nalice\ndemo\n\n\n\n\n\npytest\n"
    denied = runner.invoke(
        app, ["config", "init", "--path", str(target)], input=answers
    )
    assert denied.exit_code == 2
    assert target.read_text(encoding="utf-8") == "old"
    replaced = runner.invoke(
        app, ["config", "init", "--path", str(target), "--force"], input=answers
    )
    assert replaced.exit_code == 0
    assert "configVersion: 1" in target.read_text(encoding="utf-8")
    assert load_config(target).personal.scopeNames == ["demo"]


def test_auth_login_hides_and_stores_secret(tmp_path: Path) -> None:
    store = Store()
    result = CliRunner().invoke(
        app, ["auth", "login"], input="top-secret\n", obj=factory(tmp_path, store=store)
    )
    assert result.exit_code == 0
    assert "top-secret" not in result.stdout
    assert store.values[CredentialName.API_TOKEN] == "top-secret"


def test_bugs_mine_uses_injected_provider_scope_and_json(tmp_path: Path) -> None:
    provider = Provider()
    result = CliRunner().invoke(
        app, ["bugs", "mine", "--json"], obj=factory(tmp_path, provider=provider)
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["data"]["items"][0]["id"] == 7
    assert provider.calls == [("mine", ("demo",), 1, 20)]


def test_run_dry_run_only_prints_ordered_plan(tmp_path: Path) -> None:
    calls = 0

    def forbidden(_project: Path) -> AppRuntime:
        nonlocal calls
        calls += 1
        raise AssertionError("runtime must not be created")

    dependencies = DependencyFactory(
        forbidden, plan_builder=lambda _project: RunPlan(CONFIG)
    )
    result = CliRunner().invoke(app, ["run", "--dry-run", "--json"], obj=dependencies)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)["data"]
    assert payload["executed"] is False
    assert payload["operations"] == [
        "query_my_bugs",
        "query_bug_detail",
        "query_bug_history",
    ]
    assert calls == 0


def test_provider_exception_is_redacted_and_business_exit_three(tmp_path: Path) -> None:
    class FailingProvider(Provider):
        def query_my_bugs(self, **_kwargs: object) -> BugPage:
            raise RuntimeError("token=top-secret")

    result = CliRunner().invoke(
        app, ["bugs", "mine"], obj=factory(tmp_path, provider=FailingProvider())
    )
    assert result.exit_code == 3
    assert "top-secret" not in result.output
    structured = CliRunner().invoke(
        app,
        ["bugs", "mine", "--json"],
        obj=factory(tmp_path, provider=FailingProvider()),
    )
    assert structured.exit_code == 3
    assert json.loads(structured.stdout) == {
        "ok": False,
        "code": 3,
        "data": None,
        "error": {"type": "business", "message": "RuntimeError"},
    }


def test_auth_cancel_exits_130_without_store_write(
    tmp_path: Path, monkeypatch: object
) -> None:
    import typer

    store = Store()
    monkeypatch.setattr(
        typer, "prompt", lambda *_args, **_kwargs: (_ for _ in ()).throw(typer.Abort())
    )  # type: ignore[attr-defined]
    result = CliRunner().invoke(
        app, ["auth", "login"], obj=factory(tmp_path, store=store)
    )
    assert result.exit_code == 130
    assert not store.values


def test_doctor_json_passes_with_injected_dependencies_and_redacts_secret() -> None:
    store = TokenOnlyStore()
    result = CliRunner().invoke(
        app,
        ["doctor", "--json", "--project", str(Path.cwd())],
        obj=factory(Path.cwd(), store=store),
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["ok"] is True
    assert "doctor-token-secret" not in result.stdout
    assert store.reads == [CredentialName.API_TOKEN]


def test_doctor_passes_with_password_only_and_redacts_secret() -> None:
    result = CliRunner().invoke(
        app,
        ["doctor", "--project", str(Path.cwd())],
        obj=factory(Path.cwd(), store=PasswordOnlyStore()),
    )
    assert result.exit_code == 0
    assert "PASS credentials" in result.stdout
    assert "doctor-password-secret" not in result.stdout


def test_doctor_fails_when_credentials_are_missing() -> None:
    result = CliRunner().invoke(
        app,
        ["doctor", "--json", "--project", str(Path.cwd())],
        obj=factory(Path.cwd(), store=Store()),
    )
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    credential_check = next(
        check for check in payload["data"]["checks"] if check["name"] == "credentials"
    )
    assert credential_check["status"] == "FAIL"


def test_mcp_serve_dispatches_project_and_injected_factory(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    import zentao_ai.mcp_server.server as server_module

    dependencies = factory(tmp_path)
    calls: list[tuple[Path, object]] = []
    monkeypatch.setattr(
        server_module,
        "serve",
        lambda project, selected: calls.append((project, selected)),
    )  # type: ignore[attr-defined]
    result = CliRunner().invoke(
        app, ["mcp", "serve", "--project", str(tmp_path)], obj=dependencies
    )
    assert result.exit_code == 0
    assert calls == [(tmp_path, dependencies)]
