from __future__ import annotations
from collections.abc import Callable, Iterator
from typing import Any
from zentao_ai.zentao.models import BugPage, HistoryPage
from zentao_ai.state.models import RunStatus
from .analysis import analyze_bug
from .models import (
    AnalysisPhase,
    BugRunResult,
    Failure,
    RunContext,
    RunResult,
    SnapshotContext,
)


def _pages(
    fetch: Callable[[int, int], BugPage | HistoryPage], limit: int
) -> Iterator[Any]:
    page = 1
    yielded = 0
    while yielded < limit:
        result = fetch(page, min(100, limit - yielded))
        items = result.items
        for item in items:
            if yielded >= limit:
                return
            yield item
            yielded += 1
        coverage = result.coverage
        pages = coverage.pages or (
            (coverage.total + coverage.page_size - 1) // coverage.page_size
            if coverage.page_size
            else 1
        )
        if not items or page >= pages:
            return
        page += 1


def _history(context: RunContext, bug_id: str) -> tuple[object, ...]:
    return tuple(
        _pages(
            lambda p, s: context.provider.query_bug_history(
                bug_id, page=p, page_size=s
            ),
            1000,
        )
    )


def execute_read_workflow(
    context: RunContext,
    *,
    kind: str,
    scope_names: tuple[str, ...],
    members: tuple[str, ...] = (),
) -> RunResult:
    snap = context.snapshot or SnapshotContext.capture(context.now())
    cutoff = snap.snapshotCutoff.isoformat()
    business = snap.businessDate
    lease = context.ledger.acquire_lease(business, kind, context.owner, 3600)
    if not lease.acquired:
        return RunResult(
            str(business),
            cutoff,
            0,
            "FAILED",
            failures=(Failure("", "LEASE_UNAVAILABLE", "run already active"),),
            scopeNames=scope_names,
            members=members,
        )
    results: list[BugRunResult] = []
    failures: list[Failure] = []
    seen: set[str] = set()
    discovered = 0
    try:
        sources = (
            [lambda p, s: context.provider.query_my_bugs(page=p, page_size=s)]
            if kind == "personal"
            else [
                lambda p, s, m=m: context.provider.query_user_bugs(
                    m, page=p, page_size=s
                )
                for m in members
            ]
        )
        for source in sources:
            for listed in _pages(source, context.config.limits.maxBugsPerRun):
                key = str(listed.id)
                if key in seen:
                    continue
                seen.add(key)
                discovered += 1
                try:
                    detail = context.provider.query_bug_detail(key)
                    history = _history(context, key)
                    signal = (
                        context.analysis(detail, history, AnalysisPhase.FINAL)
                        if context.analysis
                        else None
                    )
                    results.append(
                        BugRunResult(
                            key,
                            detail.snapshot_version,
                            analyze_bug(
                                detail, history, AnalysisPhase.FINAL, signal=signal
                            ).decision,
                        )
                    )
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as exc:
                    failures.append(Failure(key, type(exc).__name__, str(exc)))
        completeness = "COMPLETE" if not failures else "PARTIAL"
        result = RunResult(
            str(business),
            cutoff,
            discovered,
            completeness,
            tuple(results),
            failures=tuple(failures),
            scopeNames=scope_names,
            members=members,
        )
        context.ledger.put_checkpoint(business, kind, result.to_v2_payload())
        if context.reportSink:
            context.reportSink.write(result.to_v2_payload())
        context.ledger.release_lease(
            lease.lease_id,
            RunStatus.SUCCEEDED if completeness == "COMPLETE" else RunStatus.FAILED,
        )
        return result
    except BaseException:
        context.ledger.release_lease(lease.lease_id, RunStatus.FAILED)
        raise
