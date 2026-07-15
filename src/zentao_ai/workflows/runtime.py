from __future__ import annotations

from datetime import timezone

from zentao_ai.state.models import RunStatus

from .analysis import analyze_bug
from .models import AnalysisPhase, BugRunResult, Failure, RunContext, RunResult


def execute_read_workflow(context: RunContext, *, kind: str, scope_names: tuple[str, ...], members: tuple[str, ...] = ()) -> RunResult:
    now = context.now()
    if now.tzinfo is None:
        cutoff = now.replace(tzinfo=timezone.utc).isoformat()
    else:
        cutoff = now.isoformat()
    business_date = now.date()
    lease = context.ledger.acquire_lease(business_date, kind, context.owner, 3600)
    if not lease.acquired:
        return RunResult(str(business_date), cutoff, 0, "FAILED", failures=(Failure("", "LEASE_UNAVAILABLE", "run already active"),), scopeNames=scope_names, members=members)
    results: list[BugRunResult] = []
    failures: list[Failure] = []
    total = 0
    try:
        pages = []
        if kind == "personal":
            pages.append(context.provider.query_my_bugs(page=1, page_size=context.config.limits.maxBugsPerRun))
        else:
            for member in members or ("",):
                pages.append(context.provider.query_user_bugs(member, page=1, page_size=context.config.limits.maxBugsPerRun))
        seen: set[str] = set()
        for page in pages:
            total += page.coverage.total
            for listed in page.items:
                key = str(listed.id)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    detail = context.provider.query_bug_detail(key)
                    history = context.provider.query_bug_history(key, page=1, page_size=100).items
                    signal = context.analysis(detail, history, AnalysisPhase.FINAL) if context.analysis else None
                    decision = analyze_bug(detail, history, AnalysisPhase.FINAL, signal=signal).decision
                    results.append(BugRunResult(key, detail.snapshot_version, decision))
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as exc:
                    failures.append(Failure(key, type(exc).__name__, str(exc)))
        completeness = "COMPLETE" if not failures and len(seen) >= total else "PARTIAL"
        payload = {"coverage": total, "processed": len(results), "failures": len(failures), "snapshotCutoff": cutoff}
        context.ledger.put_checkpoint(business_date, kind, payload)
        context.ledger.release_lease(lease.lease_id, RunStatus.SUCCEEDED if completeness == "COMPLETE" else RunStatus.FAILED)
        return RunResult(str(business_date), cutoff, total, completeness, tuple(results), failures=tuple(failures), scopeNames=scope_names, members=members)
    except BaseException:
        context.ledger.release_lease(lease.lease_id, RunStatus.FAILED)
        raise
