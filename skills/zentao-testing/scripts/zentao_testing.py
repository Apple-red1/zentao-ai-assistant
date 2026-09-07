#!/usr/bin/env python3
"""Deterministic local configuration and read-only testing workbench helpers."""
from __future__ import annotations

import argparse
import json
import sys

from assignment import AssignmentError, decide_assignment
from my_bugs import collect_my_bugs
from presenter import render_my_bugs
from project_config import (TestingConfigError, context_use, context_view, module_remove, module_set,
                            project_list, project_remove, project_set)
from testing_team import (TestingTeamError, add_global_team, add_project_team, effective_testing_team,
                          import_personal_team, remove_global_team, remove_project_team,
                          remove_project_team_override, replace_global_team, replace_project_team,
                          view_testing_team)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZenTao testing Bug workbench")
    sub = parser.add_subparsers(dest="action", required=True)

    project_set_parser = sub.add_parser("project-set", help="保存测试项目、产品和默认 affected-build")
    project_set_parser.add_argument("--alias", required=True)
    project_set_parser.add_argument("--project", help="可选的真实 Project ID 或名称")
    project_set_parser.add_argument("--product", required=True)
    project_set_parser.add_argument("--default-build", required=True)

    project_remove_parser = sub.add_parser("project-remove", help="删除一个测试项目配置")
    project_remove_parser.add_argument("--alias", required=True)
    sub.add_parser("project-list", help="列出测试项目配置")

    module_set_parser = sub.add_parser("module-set", help="保存模块及前后端负责人")
    module_set_parser.add_argument("--project-alias", required=True)
    module_set_parser.add_argument("--alias", required=True)
    module_set_parser.add_argument("--module", required=True)
    module_set_parser.add_argument("--frontend", required=True)
    module_set_parser.add_argument("--backend", required=True)

    module_remove_parser = sub.add_parser("module-remove", help="删除一个模块配置")
    module_remove_parser.add_argument("--project-alias", required=True)
    module_remove_parser.add_argument("--alias", required=True)

    context_parser = sub.add_parser("context-use", help="切换当前测试项目和模块")
    context_parser.add_argument("--project-alias", required=True)
    context_parser.add_argument("--module-alias", required=True)
    sub.add_parser("context-view", help="查看当前测试上下文")

    bugs_parser = sub.add_parser("my-bugs", help="查询当前账号未关闭 Bug")
    bugs_parser.add_argument("--all-projects", action="store_true", help="明确查询所有可见项目")
    bugs_parser.add_argument("--module", type=int, help="只保留当前模块")
    bugs_parser.add_argument("--per-page", type=int, default=1000)

    assignment_parser = sub.add_parser("assignment", help="计算并公开 Bug 分派来源")
    assignment_parser.add_argument("--frontend-account", required=True)
    assignment_parser.add_argument("--backend-account", required=True)
    assignment_parser.add_argument("--explicit-assignee")
    assignment_parser.add_argument("--side", choices=("frontend", "backend"))
    assignment_parser.add_argument("--evidence-side", choices=("frontend", "backend"))

    team_view_parser = sub.add_parser("team-view", help="查看全局默认测试团队或指定项目的生效团队")
    team_view_parser.add_argument("--project-alias")
    for action, help_text in (
        ("team-add", "添加全局默认测试团队成员"),
        ("team-remove", "移除全局默认测试团队成员"),
        ("team-replace", "替换全局默认测试团队成员"),
    ):
        command = sub.add_parser(action, help=help_text)
        command.add_argument("--member", action="append")
        if action == "team-replace":
            command.add_argument("--clear", action="store_true", help="显式保存空的全局默认测试团队")

    sub.add_parser("team-import-personal", help="明确把个人/开发团队一次性导入全局测试团队")

    project_team_view_parser = sub.add_parser("project-team-view", help="查看指定测试项目的生效测试团队")
    project_team_view_parser.add_argument("--project-alias", required=True)
    for action, help_text in (
        ("project-team-add", "添加指定测试项目覆盖团队成员"),
        ("project-team-remove", "移除指定测试项目覆盖团队成员"),
        ("project-team-replace", "替换指定测试项目覆盖团队成员"),
    ):
        command = sub.add_parser(action, help=help_text)
        command.add_argument("--project-alias", required=True)
        command.add_argument("--member", action="append")
        if action == "project-team-replace":
            command.add_argument("--clear", action="store_true", help="显式保存空的项目覆盖团队")
    project_team_reset_parser = sub.add_parser("project-team-reset", help="删除项目覆盖并回退全局默认测试团队")
    project_team_reset_parser.add_argument("--project-alias", required=True)

    for command in sub.choices.values():
        command.add_argument("--json", action="store_true", help="输出 JSON")
        command.add_argument("--markdown", action="store_true", help="my-bugs 输出 Markdown")
    return parser


def _emit(payload: object, *, markdown: bool = False) -> None:
    if markdown:
        print(render_my_bugs(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action in {"team-add", "team-remove", "team-replace", "project-team-add", "project-team-remove", "project-team-replace"}:
        if not args.member and not getattr(args, "clear", False):
            parser.error("请明确提供 --member；清空团队使用对应 replace --clear")
    if getattr(args, "clear", False) and args.action not in {"team-replace", "project-team-replace"}:
        parser.error("--clear 只能用于对应的团队 replace")
    if args.markdown and args.action != "my-bugs":
        parser.error("--markdown 仅用于 my-bugs")
    try:
        if args.action == "assignment":
            _emit(decide_assignment(frontend_account=args.frontend_account, backend_account=args.backend_account,
                                    explicit_assignee=args.explicit_assignee, explicit_side=args.side,
                                    evidence_side=args.evidence_side))
            return 0
        from zentao.runtime import get_client
        client = get_client()
        if args.action == "team-view":
            payload = view_testing_team(client, project_alias=args.project_alias)
        elif args.action == "team-add":
            payload = add_global_team(client, args.member or [])
        elif args.action == "team-remove":
            payload = remove_global_team(client, args.member or [])
        elif args.action == "team-replace":
            payload = replace_global_team(client, [] if args.clear else (args.member or []))
        elif args.action == "team-import-personal":
            payload = import_personal_team(client)
        elif args.action == "project-team-view":
            payload = effective_testing_team(client, project_alias=args.project_alias)
        elif args.action == "project-team-add":
            payload = add_project_team(client, args.project_alias, args.member or [])
        elif args.action == "project-team-remove":
            payload = remove_project_team(client, args.project_alias, args.member or [])
        elif args.action == "project-team-replace":
            payload = replace_project_team(client, args.project_alias, [] if args.clear else (args.member or []))
        elif args.action == "project-team-reset":
            payload = remove_project_team_override(client, args.project_alias)
        elif args.action == "project-set":
            payload = project_set(client, alias=args.alias, project=args.project, product=args.product,
                                  default_build=args.default_build)
        elif args.action == "project-remove":
            payload = project_remove(client, args.alias)
        elif args.action == "project-list":
            payload = project_list(client)
        elif args.action == "module-set":
            payload = module_set(client, project_alias=args.project_alias, alias=args.alias, module=args.module,
                                 frontend=args.frontend, backend=args.backend)
        elif args.action == "module-remove":
            payload = module_remove(client, project_alias=args.project_alias, alias=args.alias)
        elif args.action == "context-use":
            payload = context_use(client, project_alias=args.project_alias, module_alias=args.module_alias)
        elif args.action == "context-view":
            payload = context_view(client)
        else:
            payload = collect_my_bugs(client, all_projects=args.all_projects, module_id=args.module,
                                      per_page=args.per_page)
        _emit(payload, markdown=args.markdown)
        return 0
    except (TestingConfigError, TestingTeamError, AssignmentError) as exc:
        print(json.dumps({"error": {"code": exc.code, "message": str(exc),
                                     "details": getattr(exc, "details", {})}}, ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as exc:
        print(json.dumps({"error": {"code": "TESTING_ERROR", "message": str(exc), "details": {}}},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
