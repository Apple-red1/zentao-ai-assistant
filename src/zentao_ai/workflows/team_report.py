from .models import RunContext, TeamRunResult
from .runtime import execute_read_workflow


def run_team_report(context: RunContext) -> TeamRunResult:
    return execute_read_workflow(context, kind="team", scope_names=tuple(context.config.team.scopeNames), members=tuple(context.config.team.members))
