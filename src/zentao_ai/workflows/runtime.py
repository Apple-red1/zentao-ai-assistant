from __future__ import annotations
from collections.abc import Callable, Iterator
from typing import Any
from zentao_ai.routing.models import BugSnapshot as RoutingSnapshot
from zentao_ai.routing.router import route_bug
from zentao_ai.zentao.models import BugPage, HistoryPage
from zentao_ai.state.models import RunStatus
from .analysis import analyze_bug
from .models import (
    AnalysisPhase,
    BugRunResult,
    Decision,
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
    routing_incomplete = False
    try:

        def personal_source(page: int, page_size: int) -> BugPage:
            account = context.config.zentao.account
            if account:
                return context.provider.query_user_bugs(
                    account,
                    scope_names=(),
                    page=page,
                    page_size=page_size,
                    browse_type="assigntome",
                )
            return context.provider.query_my_bugs(
                scope_names=scope_names, page=page, page_size=page_size
            )

        def member_source(member: str) -> Callable[[int, int], BugPage]:
            def fetch(page: int, page_size: int) -> BugPage:
                return context.provider.query_user_bugs(
                    member, scope_names=scope_names, page=page, page_size=page_size
                )

            return fetch

        sources = (
            [personal_source]
            if kind == "personal"
            else [member_source(member) for member in members]
        )
        total = 0
        total_known = True
        limit = context.config.limits.maxBugsPerRun
        discovery_page_size = min(20, limit)
        for source in sources:
            first_page = source(1, discovery_page_size)
            if first_page.coverage.total < len(first_page.items):
                total_known = False
            else:
                total += first_page.coverage.total
            expected = first_page.coverage
            page_count = expected.pages or (
                (expected.total + expected.page_size - 1) // expected.page_size
                if expected.page_size
                else 1
            )
            page = first_page
            page_number = 1
            while True:
                coverage = page.coverage
                if (
                    coverage.total != expected.total
                    or coverage.page_size != expected.page_size
                    or coverage.pages != expected.pages
                    or coverage.total < len(page.items)
                ):
                    total_known = False
                for listed in page.items:
                    if discovered >= limit:
                        break
                    key = str(listed.id)
                    if key in seen:
                        continue
                    seen.add(key)
                    discovered += 1
                    try:
                        detail = context.provider.query_bug_detail(key)
                        history_failed = False
                        try:
                            history = _history(context, key)
                        except (KeyboardInterrupt, SystemExit):
                            raise
                        except Exception as exc:
                            history = ()
                            history_failed = True
                            failures.append(Failure(key, type(exc).__name__, str(exc)))
                        signal = (
                            context.analysis(detail, history, AnalysisPhase.FINAL)
                            if context.analysis
                            else None
                        )
                        provider_routing = detail.routing
                        selected_repository: str | None
                        if (
                            provider_routing is not None
                            and provider_routing.selected_repository is not None
                        ):
                            selected_repository = provider_routing.selected_repository
                            layer = provider_routing.layer
                            candidates = provider_routing.repositories
                            matched_keywords = provider_routing.matched_keywords
                        else:
                            routing = route_bug(
                                RoutingSnapshot(
                                    identifier=key,
                                    title=detail.title,
                                    description=detail.steps,
                                ),
                                context.config,
                            )
                            selected_repository = routing.selectedRepository
                            layer = routing.layer
                            candidates = tuple(routing.candidates)
                            matched_keywords = tuple(routing.matchedKeywords)
                        decision = analyze_bug(
                            detail, history, AnalysisPhase.FINAL, signal=signal
                        ).decision
                        routing_status = "ROUTED" if selected_repository else "UNKNOWN"
                        if history_failed or (
                            kind == "personal" and selected_repository is None
                        ):
                            routing_incomplete = True
                            decision = Decision.NEEDS_ENGINEER_REVIEW
                        results.append(
                            BugRunResult(
                                key,
                                detail.snapshot_version,
                                decision,
                                selectedRepository=selected_repository,
                                layer=layer,
                                candidates=candidates,
                                matchedKeywords=matched_keywords,
                                routingStatus=routing_status,
                            )
                        )
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except Exception as exc:
                        failures.append(Failure(key, type(exc).__name__, str(exc)))
                page_number += 1
                if not page.items or page_number > page_count or discovered >= limit:
                    break
                page = source(page_number, discovery_page_size)
        truncated = (not total_known) or total > discovered
        completeness = (
            "COMPLETE"
            if not failures and not truncated and not routing_incomplete
            else "PARTIAL"
        )
        result = RunResult(
            str(business),
            cutoff,
            discovered,
            completeness,
            tuple(results),
            failures=tuple(failures),
            scopeNames=scope_names,
            members=members,
            coverageTotal=total if total_known else None,
            truncated=truncated,
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
