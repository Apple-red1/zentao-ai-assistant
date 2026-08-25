from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from ..internal.config import encode_env_value, project_root, write_private_text_atomic
from ..internal.errors import ConfigError, UsageError, ZentaoError
from ..services.container import Services
from .common import Parser, add_json_flag
from .output import emit_error, emit_success
from .bugs import commands as cmd_bugs
from .builds import commands as cmd_builds
from .epics import commands as cmd_epics
from .executions import commands as cmd_executions
from .feedbacks import commands as cmd_feedbacks
from .files import commands as cmd_files
from .resources import commands as cmd_resources
from .products import commands as cmd_products
from .product_plans import commands as cmd_product_plans
from .programs import commands as cmd_programs
from .projects import commands as cmd_projects
from .releases import commands as cmd_releases
from .requirements import commands as cmd_requirements
from .stories import commands as cmd_stories
from .systems import commands as cmd_systems
from .tasks import commands as cmd_tasks
from .test_cases import commands as cmd_test_cases
from .test_tasks import commands as cmd_test_tasks
from .tickets import commands as cmd_tickets
from .users import commands as cmd_users


CLI_ENDPOINT_IDS = frozenset({"token.login"}).union(cmd_bugs.ENDPOINT_IDS, cmd_builds.ENDPOINT_IDS, cmd_epics.ENDPOINT_IDS, cmd_executions.ENDPOINT_IDS, cmd_feedbacks.ENDPOINT_IDS, cmd_files.ENDPOINT_IDS, cmd_products.ENDPOINT_IDS, cmd_product_plans.ENDPOINT_IDS, cmd_programs.ENDPOINT_IDS, cmd_projects.ENDPOINT_IDS, cmd_releases.ENDPOINT_IDS, cmd_requirements.ENDPOINT_IDS, cmd_stories.ENDPOINT_IDS, cmd_systems.ENDPOINT_IDS, cmd_tasks.ENDPOINT_IDS, cmd_test_cases.ENDPOINT_IDS, cmd_test_tasks.ENDPOINT_IDS, cmd_tickets.ENDPOINT_IDS, cmd_users.ENDPOINT_IDS)

class Context:
    def __init__(self) -> None:
        self._services: Services | None = None

    @property
    def services(self) -> Services:
        if self._services is None:
            self._services = Services()
        return self._services

def build_parser() -> Parser:
    parser = Parser(prog="zentao.py", description="ZenTao API v2 Skill CLI")
    top = parser.add_subparsers(dest="resource", required=True)

    setup = top.add_parser("setup", help="写入项目根目录 .env")
    setup.add_argument("--base-url")
    setup.add_argument("--account")
    add_json_flag(setup)
    setup.set_defaults(_handler=_run_setup)

    doctor = top.add_parser("doctor", help="验证 .env 配置并登录 API v2")
    add_json_flag(doctor)
    doctor.set_defaults(_handler=_run_doctor)

    r_bug = top.add_parser('bug', help='bug resource')
    r_bug_actions = r_bug.add_subparsers(dest="action", required=True)
    cmd_bugs.register(r_bug_actions)

    r_build = top.add_parser('build', help='build resource')
    r_build_actions = r_build.add_subparsers(dest="action", required=True)
    cmd_builds.register(r_build_actions)

    r_epic = top.add_parser('epic', help='epic resource')
    r_epic_actions = r_epic.add_subparsers(dest="action", required=True)
    cmd_epics.register(r_epic_actions)

    r_execution = top.add_parser('execution', help='execution resource')
    r_execution_actions = r_execution.add_subparsers(dest="action", required=True)
    cmd_executions.register(r_execution_actions)

    r_feedback = top.add_parser('feedback', help='feedback resource')
    r_feedback_actions = r_feedback.add_subparsers(dest="action", required=True)
    cmd_feedbacks.register(r_feedback_actions)

    r_file = top.add_parser('file', help='file resource')
    r_file_actions = r_file.add_subparsers(dest="action", required=True)
    cmd_files.register(r_file_actions)

    r_resource = top.add_parser('resource', help='ZenTao object related resource files')
    r_resource_actions = r_resource.add_subparsers(dest="action", required=True)
    cmd_resources.register(r_resource_actions)

    r_product = top.add_parser('product', help='product resource')
    r_product_actions = r_product.add_subparsers(dest="action", required=True)
    cmd_products.register(r_product_actions)

    r_product_plan = top.add_parser('product-plan', help='product-plan resource')
    r_product_plan_actions = r_product_plan.add_subparsers(dest="action", required=True)
    cmd_product_plans.register(r_product_plan_actions)

    r_program = top.add_parser('program', help='program resource')
    r_program_actions = r_program.add_subparsers(dest="action", required=True)
    cmd_programs.register(r_program_actions)

    r_project = top.add_parser('project', help='project resource')
    r_project_actions = r_project.add_subparsers(dest="action", required=True)
    cmd_projects.register(r_project_actions)

    r_release = top.add_parser('release', help='release resource')
    r_release_actions = r_release.add_subparsers(dest="action", required=True)
    cmd_releases.register(r_release_actions)

    r_requirement = top.add_parser('requirement', help='requirement resource')
    r_requirement_actions = r_requirement.add_subparsers(dest="action", required=True)
    cmd_requirements.register(r_requirement_actions)

    r_story = top.add_parser('story', help='story resource')
    r_story_actions = r_story.add_subparsers(dest="action", required=True)
    cmd_stories.register(r_story_actions)

    r_system = top.add_parser('system', help='system resource')
    r_system_actions = r_system.add_subparsers(dest="action", required=True)
    cmd_systems.register(r_system_actions)

    r_task = top.add_parser('task', help='task resource')
    r_task_actions = r_task.add_subparsers(dest="action", required=True)
    cmd_tasks.register(r_task_actions)

    r_test_case = top.add_parser('test-case', help='test-case resource')
    r_test_case_actions = r_test_case.add_subparsers(dest="action", required=True)
    cmd_test_cases.register(r_test_case_actions)

    r_test_task = top.add_parser('test-task', help='test-task resource')
    r_test_task_actions = r_test_task.add_subparsers(dest="action", required=True)
    cmd_test_tasks.register(r_test_task_actions)

    r_ticket = top.add_parser('ticket', help='ticket resource')
    r_ticket_actions = r_ticket.add_subparsers(dest="action", required=True)
    cmd_tickets.register(r_ticket_actions)

    r_user = top.add_parser('user', help='user resource')
    r_user_actions = r_user.add_subparsers(dest="action", required=True)
    cmd_users.register(r_user_actions)

    return parser

def _run_setup(_: object, args: argparse.Namespace) -> object:
    base_url = args.base_url or input("ZenTao Base URL: ").strip()
    account = args.account or input("ZenTao Account: ").strip()
    password = getpass.getpass("ZenTao Password: ")
    if not base_url or not account or not password:
        raise UsageError("base URL、account、password 都不能为空")
    env_path = project_root() / ".env"
    content = "ZENTAO_BASE_URL=" + encode_env_value(base_url.rstrip("/")) + "\n" + "ZENTAO_ACCOUNT=" + encode_env_value(account) + "\n" + "ZENTAO_PASSWORD=" + encode_env_value(password) + "\n"
    write_private_text_atomic(env_path, content)
    return {"status": "success", "path": str(env_path)}

def _run_doctor(services: object, _: argparse.Namespace) -> object:
    assert isinstance(services, Services)
    services.session.ensure_login()
    return {"status": "ok", "base_url": services.session.config.base_url, "account": services.session.config.account}

def main(argv: list[str] | None = None) -> int:
    argsv = list(sys.argv[1:] if argv is None else argv)
    json_requested = "--json" in argsv
    parser = build_parser()
    context = Context()
    try:
        args = parser.parse_args(argsv)
        result = args._handler(context.services if args.resource == "doctor" else (None if args.resource == "setup" else context.services), args)
        emit_success(result, json_output=bool(getattr(args, "json_output", False)))
        return 0
    except KeyboardInterrupt:
        return 130
    except ZentaoError as exc:
        emit_error(exc, json_output=json_requested)
        return exc.exit_code
    except (FileNotFoundError, OSError) as exc:
        err = UsageError(str(exc))
        emit_error(err, json_output=json_requested)
        return err.exit_code
