from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import ValidationError

from zentao_ai.actions import BugActionService
from zentao_ai.bugs import BugService
from zentao_ai.client import ZentaoClient
from zentao_ai.config import ConfigError, load_settings, save_settings
from zentao_ai.credentials import KeyringCredentialStore
from zentao_ai.errors import ZentaoError
from zentao_ai.models import (
    BugFilters,
    Settings,
    TeamMember,
    TeamSettings,
    ZentaoSettings,
)
from zentao_ai.server import McpServices, ZentaoMcpServer
from zentao_ai.users import UserDirectory

app = typer.Typer(
    name="zentao-ai",
    help="禅道 21.7.8 的本地 Codex Bug 助手。",
    no_args_is_help=True,
)
mcp_app = typer.Typer(help="运行 Codex 使用的 MCP 服务。")
app.add_typer(mcp_app, name="mcp")

DOCTOR_CHECK_NAMES = (
    "CONFIG",
    "CREDENTIALS",
    "LOGIN",
    "API_V2",
    "TEAM_MEMBERS",
    "QUERY_MY_BUGS",
    "EDIT",
    "COMMENT",
    "ACTIVATE",
    "ASSIGN",
    "MCP",
)

CheckState = Literal["PASS", "WARN", "FAIL"]
ConfigOption = Annotated[
    Path | None,
    typer.Option("--config", help="配置文件路径；默认使用 ~/.codex/zentao-ai-bug/config.yaml。"),
]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    state: CheckState
    detail: str
    required: bool = False


def credential_store() -> KeyringCredentialStore:
    return KeyringCredentialStore()


@app.command()
def setup(
    config: ConfigOption = None,
    update: Annotated[bool, typer.Option("--update", help="更新已有配置。")]=False,
) -> None:
    """交互式创建本地配置；密码只写入系统凭据库。"""
    path = config.expanduser() if config else None
    existing: Settings | None = None
    target = path
    if target is not None and target.exists():
        if not update:
            typer.echo(f"配置已存在：{target}；如需更新请添加 --update。", err=True)
            raise typer.Exit(code=2)
        existing = load_settings(target)

    default_url = str(existing.zentao.base_url) if existing else None
    default_account = existing.zentao.account if existing else None
    base_url = typer.prompt("禅道地址", default=default_url).strip()
    account = typer.prompt("个人账号", default=default_account).strip()
    password = typer.prompt("个人密码（只保存到系统凭据库）", hide_input=True)
    existing_members = (
        ",".join(f"{item.name}={item.account}" for item in existing.team.members)
        if existing
        else ""
    )
    team_text = typer.prompt(
        "团队成员（姓名=账号，多个用逗号分隔，可留空）",
        default=existing_members,
        show_default=bool(existing_members),
    )

    try:
        settings = Settings(
            version=1,
            zentao=ZentaoSettings(base_url=base_url, account=account),
            team=TeamSettings(members=_parse_team(team_text)),
        )
    except (ValidationError, ValueError) as exc:
        typer.echo("配置格式无效，请检查地址、账号和团队成员格式。", err=True)
        raise typer.Exit(code=2) from exc

    saved = save_settings(settings, target)
    credential_store().set_password(str(settings.zentao.base_url), account, password)
    typer.echo(f"配置完成：{saved}")
    typer.echo("下一步运行：zentao-ai doctor")


@app.command()
def doctor(config: ConfigOption = None) -> None:
    """检查本地配置、登录、查询、团队与 MCP 能力。"""
    try:
        settings = load_settings(config)
    except ConfigError:
        typer.echo("FAIL CONFIG: 找不到或无法读取本地配置。")
        raise typer.Exit(code=2) from None

    checks = asyncio.run(_doctor_checks(settings, credential_store()))
    for check in checks:
        typer.echo(f"{check.state} {check.name}: {check.detail}")
    if any(check.required and check.state == "FAIL" for check in checks):
        raise typer.Exit(code=2)


@mcp_app.command("serve")
def mcp_serve(config: ConfigOption = None) -> None:
    """通过标准输入输出运行 MCP Server。"""
    try:
        settings = load_settings(config)
        server = _build_server(settings, credential_store())
    except (ConfigError, ValidationError):
        typer.echo("无法启动 MCP：本地配置无效。", err=True)
        raise typer.Exit(code=2) from None
    server.run_stdio()


def _parse_team(value: str) -> list[TeamMember]:
    if not value.strip():
        return []
    members: list[TeamMember] = []
    for item in value.replace("，", ",").split(","):
        if not item.strip():
            continue
        if "=" not in item:
            raise ValueError("team member must use name=account")
        name, account = item.split("=", 1)
        members.append(TeamMember(name=name.strip(), account=account.strip()))
    return members


def _build_server(
    settings: Settings,
    store: KeyringCredentialStore,
) -> ZentaoMcpServer:
    client = ZentaoClient(settings, store)
    users = UserDirectory(client)
    bugs = BugService(client, settings)
    actions = BugActionService(client, bugs, users, settings)
    return ZentaoMcpServer(
        McpServices(
            settings=settings,
            bugs=bugs,
            actions=actions,
            users=users,
        )
    )


async def _doctor_checks(
    settings: Settings,
    store: KeyringCredentialStore,
) -> list[DoctorCheck]:
    checks = [DoctorCheck("CONFIG", "PASS", "配置结构有效。", required=True)]
    password = store.get_password(str(settings.zentao.base_url), settings.zentao.account)
    if not password:
        checks.extend(
            [
                DoctorCheck("CREDENTIALS", "FAIL", "系统凭据库中没有密码。", required=True),
                DoctorCheck("LOGIN", "FAIL", "未尝试登录。", required=True),
                DoctorCheck("API_V2", "FAIL", "未验证 API v2。", required=True),
                DoctorCheck("TEAM_MEMBERS", "WARN", "未验证团队成员。"),
                DoctorCheck("QUERY_MY_BUGS", "FAIL", "未验证个人 Bug 查询。", required=True),
            ]
        )
        checks.extend(_write_checks(settings))
        checks.append(DoctorCheck("MCP", "PASS", "MCP 工具合同可加载。", required=True))
        return checks

    checks.append(DoctorCheck("CREDENTIALS", "PASS", "密码已安全保存。", required=True))
    try:
        async with ZentaoClient(settings, store) as client:
            await client.request_json(
                "GET",
                "/users",
                params={"browseType": "inside", "page": 1, "recPerPage": 1},
            )
            checks.append(DoctorCheck("LOGIN", "PASS", "登录成功。", required=True))
            checks.append(DoctorCheck("API_V2", "PASS", "API v2 可用。", required=True))
            users = UserDirectory(client)
            validation = await users.validate_team(settings.team.members)
            if validation.failures:
                checks.append(
                    DoctorCheck(
                        "TEAM_MEMBERS",
                        "WARN",
                        f"{len(validation.failures)} 个团队成员配置未匹配。",
                    )
                )
            else:
                checks.append(
                    DoctorCheck(
                        "TEAM_MEMBERS",
                        "PASS",
                        f"已验证 {len(validation.resolved)} 个团队成员。",
                    )
                )
            bugs = BugService(client, settings)
            await bugs.query_my_bugs(BugFilters(max_results=1))
            checks.append(
                DoctorCheck("QUERY_MY_BUGS", "PASS", "个人 Bug 查询可用。", required=True)
            )
    except ZentaoError as exc:
        existing = {check.name for check in checks}
        for name in ("LOGIN", "API_V2", "TEAM_MEMBERS", "QUERY_MY_BUGS"):
            if name not in existing:
                checks.append(
                    DoctorCheck(
                        name,
                        "FAIL" if name != "TEAM_MEMBERS" else "WARN",
                        exc.message,
                        required=name != "TEAM_MEMBERS",
                    )
                )

    checks.extend(_write_checks(settings))
    server = _build_server(settings, store)
    names = await server.list_tool_names()
    checks.append(
        DoctorCheck(
            "MCP",
            "PASS" if len(names) == 10 else "FAIL",
            f"已加载 {len(names)} 个工具。",
            required=True,
        )
    )
    return checks


def _write_checks(settings: Settings) -> list[DoctorCheck]:
    state: CheckState = "PASS" if settings.writes.enabled else "WARN"
    detail = "本地写操作已启用。" if settings.writes.enabled else "本地写操作已关闭。"
    return [
        DoctorCheck(name, state, detail)
        for name in ("EDIT", "COMMENT", "ACTIVATE", "ASSIGN")
    ]


if __name__ == "__main__":
    app()
