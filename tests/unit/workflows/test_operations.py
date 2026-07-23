from __future__ import annotations

from datetime import datetime

from zentao_ai.config.models import AppConfig
from zentao_ai.workflows.models import AnalysisSignal, RunContext
from zentao_ai.workflows.personal import run_personal
from zentao_ai.workflows.team_report import run_team_report
from zentao_ai.zentao.models import BugPage, BugSnapshot, Coverage, HistoryPage


class Provider:
    writes = 0
    def query_my_bugs(self, **_): return BugPage(items=(self.query_bug_detail(1),), coverage=Coverage(total=1))
    def query_user_bugs(self, user, **_): return self.query_my_bugs()
    def query_bug_detail(self, bug_id, *, allow_unstable=False): return BugSnapshot(id=bug_id, status="active", version="v1", snapshotVersion="v1")
    def query_bug_history(self, bug_id, **_): return HistoryPage(items=(), coverage=Coverage(total=0))


class Ledger:
    def acquire_lease(self, *_): return type("Lease", (), {"acquired": True, "lease_id": "l"})()
    def release_lease(self, *_): pass
    def put_checkpoint(self, *_): pass


def ctx():
    cfg = AppConfig.model_validate({"personal":{"scopeNames":["mine"]},"team":{"scopeNames":["team"],"members":["a"]},"repositories":{}})
    return RunContext(cfg, Provider(), Ledger(), lambda: datetime(2026,7,15,9), "owner", analysis=lambda *_: AnalysisSignal(evidenceComplete=True, fixCandidate=True))


def test_personal_and_team_share_cutoff_but_keep_scope_contracts():
    personal, team = run_personal(ctx()), run_team_report(ctx())
    assert personal.snapshotCutoff == team.snapshotCutoff
    assert personal.scopeNames == ("mine",) and team.scopeNames == ("team",)
    assert team.members == ("a",) and team.completeness == "COMPLETE"
