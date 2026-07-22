from __future__ import annotations

import json
from pathlib import Path
import pytest
from pydantic import SecretStr

from typer.testing import CliRunner

from zentao_ai.cli.app import app
from zentao_ai.cli.bug_commands import _placeholder
from zentao_ai.cli.runtime import AppRuntime, DependencyFactory, RunPlan
from zentao_ai.config.models import AppConfig
from zentao_ai.config.loader import load_config
from zentao_ai.credentials.store import CredentialName
from zentao_ai.safety import ActionRequest, AuthorizationContext, authorize
from zentao_ai.zentao.models import (
    BugPage,
    BugSnapshot,
    Coverage,
    ItemFailure,
    ResolvedIdentity,
)


CONFIG = AppConfig.model_validate(
    {
        "configVersion": 1,
        "zentao": {"account": "weiwenting"},
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


def test_transport_placeholder_is_explicitly_stable() -> None:
    placeholder = _placeholder("3422")

    assert placeholder.version == "transport"
    assert placeholder.snapshot_version == "transport"
    assert placeholder.snapshot_stable is True


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

    def query_user_bugs(
        self,
        user: str,
        *,
        scope_names: tuple[str, ...],
        page: int,
        page_size: int,
        browse_type: str | None = None,
    ) -> BugPage:
        self.calls.append(("user", user, scope_names, page, page_size, browse_type))
        return BugPage(
            items=(
                BugSnapshot(
                    id=2537,
                    title="【AI建站】 first",
                    status="active",
                    version="v1",
                    snapshotVersion="s1",
                ),
                BugSnapshot(
                    id=3397,
                    title="【站点后台】 second",
                    status="open",
                    version="v1",
                    snapshotVersion="s2",
                ),
            ),
            coverage=Coverage(page=1, pageSize=20, total=2, pages=1),
        )

    def bug_statistics(self) -> dict[str, int]:
        return {"active": 1}


def factory(
    tmp_path: Path,
    provider: Provider | None = None,
    store: Store | None = None,
    config: AppConfig = CONFIG,
) -> DependencyFactory:
    runtime = AppRuntime(
        config,
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


def test_confirmed_repair_builds_exact_comment_and_write_code_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import zentao_ai.cli.bug_commands as commands

    captured: dict[str, object] = {}
    original_normalize = commands.normalize_cli_request

    def capture_request(payload: object):
        request = original_normalize(payload)  # type: ignore[arg-type]
        captured["actions"] = request.actions
        return request

    def probe(context: object, bug_id: int | str) -> dict[str, object]:
        captured["records"] = context.authorizationRecords  # type: ignore[attr-defined]
        decision = authorize(
            ActionRequest(action="write_code", bugId=str(bug_id), parameters={}),
            AuthorizationContext(
                codeWriteEnabled=True,
                routingUnique=True,
                repositoryGuardPassed=True,
                snapshotStable=False,
                currentTurnId=context.currentTurnId,  # type: ignore[attr-defined]
                authorizationRecords=context.authorizationRecords,  # type: ignore[attr-defined]
            ),
        )
        return {"writeCodeAllowed": decision.allowed}

    monkeypatch.setattr(commands, "normalize_cli_request", capture_request)
    monkeypatch.setattr(commands, "repair_bug", probe)

    result = CliRunner().invoke(
        app,
        [
            "repair",
            "3422",
            "--confirm",
            "--turn-id",
            "turn-1",
            "--json",
            "--project",
            str(tmp_path),
        ],
        obj=factory(tmp_path),
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["data"]["writeCodeAllowed"] is True
    assert [item.action for item in captured["actions"]] == [  # type: ignore[union-attr]
        "comment",
        "write_code",
    ]
    assert [item.action for item in captured["records"]] == [  # type: ignore[union-attr]
        "comment",
        "write_code",
    ]


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


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        (["--title-tag", "AI建站", "--status", "all"], [2537]),
        (["--title-tag", "站点后台", "--status", "unclosed"], [3397]),
        (["--status", "unclosed"], [2537, 3397]),
    ],
)
def test_bugs_mine_uses_configured_user_endpoint_and_filters(
    tmp_path: Path, options: list[str], expected: list[int]
) -> None:
    provider = Provider()
    result = CliRunner().invoke(
        app,
        ["bugs", "mine", *options, "--json"],
        obj=factory(tmp_path, provider=provider),
    )
    assert result.exit_code == 0
    assert [
        item["id"] for item in json.loads(result.stdout)["data"]["items"]
    ] == expected
    assert provider.calls == [("user", "weiwenting", (), 1, 20, "assigntome")]


def test_bugs_user_session_visible_queries_explicit_user_without_team_membership(
    tmp_path: Path,
) -> None:
    provider = Provider()
    config_before = CONFIG.model_dump()

    result = CliRunner().invoke(
        app,
        [
            "bugs",
            "user",
            "周海韵",
            "--scope-mode",
            "session-visible",
            "--status",
            "unclosed",
            "--json",
        ],
        obj=factory(tmp_path, provider=provider),
    )

    assert result.exit_code == 0
    assert [item["id"] for item in json.loads(result.stdout)["data"]["items"]] == [
        2537,
        3397,
    ]
    assert provider.calls == [("user", "周海韵", (), 1, 20, None)]
    assert CONFIG.model_dump() == config_before


def test_bugs_user_renders_markdown_table_with_unstable_row(tmp_path: Path) -> None:
    class UnstableProvider(Provider):
        def query_user_bugs(
            self,
            user: str,
            *,
            scope_names: tuple[str, ...],
            page: int,
            page_size: int,
            browse_type: str | None = None,
        ) -> BugPage:
            return BugPage(
                items=(
                    BugSnapshot(
                        id=3422,
                        title="SEO | Rule\nTwitter",
                        priority="P3",
                        status="active",
                        assignee="zhouhaiyin",
                        version=None,
                        snapshotVersion=None,
                        snapshotStable=False,
                    ),
                ),
                coverage=Coverage(
                    total=1,
                    pages=1,
                    returned=1,
                    complete=True,
                    unstableSnapshots=1,
                ),
            )

    result = CliRunner().invoke(
        app,
        [
            "bugs",
            "user",
            "周海音",
            "--scope-mode",
            "session-visible",
            "--status",
            "unclosed",
        ],
        obj=factory(tmp_path, provider=UnstableProvider()),
    )

    assert result.exit_code == 0
    assert "| Bug号 | 标题 | 优先级 | 状态 | 负责人 | 快照稳定性 |" in result.stdout
    assert (
        "| 3422 | SEO &#124; Rule Twitter | P3 | active | zhouhaiyin | 不稳定 |"
        in result.stdout
    )


def test_bugs_user_markdown_table_keeps_unknown_fields_visible(tmp_path: Path) -> None:
    class SparseProvider(Provider):
        def query_user_bugs(
            self,
            user: str,
            *,
            scope_names: tuple[str, ...],
            page: int,
            page_size: int,
            browse_type: str | None = None,
        ) -> BugPage:
            return BugPage(
                items=(
                    BugSnapshot(
                        id=3423,
                        title="",
                        priority=" ",
                        status="active",
                        assignee=None,
                        version="v1",
                        snapshotVersion="v1",
                        snapshotStable=True,
                    ),
                ),
                coverage=Coverage(total=1, pages=1, returned=1),
            )

    result = CliRunner().invoke(
        app,
        ["bugs", "user", "周海音", "--scope-mode", "session-visible"],
        obj=factory(tmp_path, provider=SparseProvider()),
    )

    assert result.exit_code == 0
    assert "| 3423 | unknown | unknown | active | unknown | 稳定 |" in result.stdout


def test_bugs_user_markdown_table_encodes_pipe_after_backslash(tmp_path: Path) -> None:
    class BackslashProvider(Provider):
        def query_user_bugs(
            self,
            user: str,
            *,
            scope_names: tuple[str, ...],
            page: int,
            page_size: int,
            browse_type: str | None = None,
        ) -> BugPage:
            return BugPage(
                items=(
                    BugSnapshot(
                        id=3424,
                        title=r"foo\|bar",
                        priority="P2",
                        status="active",
                        assignee="alice",
                        version="v1",
                        snapshotVersion="v1",
                        snapshotStable=True,
                    ),
                ),
                coverage=Coverage(total=1, pages=1, returned=1),
            )

    result = CliRunner().invoke(
        app,
        ["bugs", "user", "alice", "--scope-mode", "session-visible"],
        obj=factory(tmp_path, provider=BackslashProvider()),
    )

    assert result.exit_code == 0
    row = next(line for line in result.stdout.splitlines() if "3424" in line)
    assert row == r"| 3424 | foo\&#124;bar | P2 | active | alice | 稳定 |"
    assert row.count("|") == 7


def test_bugs_user_json_preserves_structured_data_items(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "bugs",
            "user",
            "周海韵",
            "--scope-mode",
            "session-visible",
            "--json",
        ],
        obj=factory(tmp_path),
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert [item["id"] for item in payload["data"]["items"]] == [2537, 3397]


def test_bugs_mine_renders_markdown_table(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["bugs", "mine", "--status", "unclosed"],
        obj=factory(tmp_path),
    )

    assert result.exit_code == 0
    assert "| Bug号 | 标题 | 优先级 | 状态 | 负责人 | 快照稳定性 |" in result.stdout
    assert "| 2537 | 【AI建站】 first | unknown | active | unknown | 不稳定 |" in result.stdout


def test_bugs_mine_distrusts_multi_page_total_when_visible_items_all_pass(
    tmp_path: Path,
) -> None:
    class MultiPageProvider(Provider):
        def query_user_bugs(
            self,
            user: str,
            *,
            scope_names: tuple[str, ...],
            page: int,
            page_size: int,
            browse_type: str | None = None,
        ) -> BugPage:
            source = super().query_user_bugs(
                user,
                scope_names=scope_names,
                page=page,
                page_size=page_size,
                browse_type=browse_type,
            )
            return source.model_copy(
                update={"coverage": Coverage(page=1, pageSize=20, total=40, pages=2)}
            )

    provider = MultiPageProvider()
    result = CliRunner().invoke(
        app,
        ["bugs", "mine", "--status", "unclosed", "--json"],
        obj=factory(tmp_path, provider=provider),
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)["data"]
    assert [item["id"] for item in payload["items"]] == [2537, 3397]
    assert payload["coverage"] == {
        "page": 1,
        "pageSize": 20,
        "total": -1,
        "pages": None,
        "returned": 2,
        "failed": 0,
        "complete": False,
        "unstableSnapshots": 0,
    }


def test_bugs_mine_preserves_partial_result_metadata(tmp_path: Path) -> None:
    class PartialProvider(Provider):
        def query_user_bugs(
            self,
            user: str,
            *,
            scope_names: tuple[str, ...],
            page: int,
            page_size: int,
            browse_type: str | None = None,
        ) -> BugPage:
            source = super().query_user_bugs(
                user,
                scope_names=scope_names,
                page=page,
                page_size=page_size,
                browse_type=browse_type,
            )
            return BugPage(
                items=source.items,
                coverage=Coverage(
                    page=1,
                    pageSize=20,
                    total=-1,
                    pages=None,
                    returned=2,
                    failed=1,
                    complete=False,
                ),
                itemFailures=(
                    ItemFailure(
                        bugId="3398",
                        code="MISSING_STABLE_VERSION",
                        field="version",
                        message="missing stable version",
                    ),
                ),
                resolvedIdentity=ResolvedIdentity(
                    requestedIdentity="weiwenting",
                    resolvedAccount="wwt",
                    resolvedDisplayName="Wei Wen Ting",
                    matchType="display_name",
                ),
            )

    result = CliRunner().invoke(
        app,
        ["bugs", "mine", "--json"],
        obj=factory(tmp_path, provider=PartialProvider()),
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)["data"]
    assert payload["coverage"] == {
        "page": 1,
        "pageSize": 20,
        "total": -1,
        "pages": None,
        "returned": 2,
        "failed": 1,
        "complete": False,
        "unstableSnapshots": 0,
    }
    assert payload["itemFailures"][0]["bugId"] == "3398"
    assert payload["resolvedIdentity"]["resolvedAccount"] == "wwt"


def test_bugs_mine_distrusts_zero_pages_with_nonempty_items(tmp_path: Path) -> None:
    class ContradictoryProvider(Provider):
        def query_user_bugs(
            self,
            user: str,
            *,
            scope_names: tuple[str, ...],
            page: int,
            page_size: int,
            browse_type: str | None = None,
        ) -> BugPage:
            source = super().query_user_bugs(
                user,
                scope_names=scope_names,
                page=page,
                page_size=page_size,
                browse_type=browse_type,
            )
            return BugPage(
                items=source.items[:1],
                coverage=Coverage(page=1, pageSize=20, total=1, pages=0),
            )

    result = CliRunner().invoke(
        app,
        ["bugs", "mine", "--json"],
        obj=factory(tmp_path, provider=ContradictoryProvider()),
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)["data"]
    assert [item["id"] for item in payload["items"]] == [2537]
    assert payload["coverage"] == {
        "page": 1,
        "pageSize": 20,
        "total": -1,
        "pages": None,
        "returned": 1,
        "failed": 0,
        "complete": False,
        "unstableSnapshots": 0,
    }


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
        def query_user_bugs(self, *_args: object, **_kwargs: object) -> BugPage:
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


def test_doctor_without_configured_account_uses_current_user_provider_query() -> None:
    provider = Provider()
    store = TokenOnlyStore()
    config = CONFIG.model_copy(
        update={"zentao": CONFIG.zentao.model_copy(update={"account": None})}
    )

    result = CliRunner().invoke(
        app,
        ["doctor", "--json", "--project", str(Path.cwd())],
        obj=factory(Path.cwd(), provider=provider, store=store, config=config),
    )

    assert result.exit_code == 0
    assert ("mine", ("demo",), 1, 1) in provider.calls


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
