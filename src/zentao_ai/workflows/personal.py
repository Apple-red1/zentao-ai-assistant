from .models import PersonalRunResult, RunContext
from .runtime import execute_read_workflow


def run_personal(context: RunContext) -> PersonalRunResult:
    return execute_read_workflow(context, kind="personal", scope_names=tuple(context.config.personal.scopeNames))
