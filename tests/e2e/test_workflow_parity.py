from zentao_ai.workflows.analysis import analyze_bug
from zentao_ai.workflows.models import AnalysisPhase, AnalysisSignal
from zentao_ai.zentao.models import BugSnapshot


def test_cli_and_codex_equivalent_inputs_have_same_decision():
    payload = {"id":1,"status":"active","version":"v1","snapshotVersion":"v1"}
    cli = BugSnapshot.model_validate(payload)
    codex = BugSnapshot.model_validate_json('{"id":1,"status":"active","version":"v1","snapshotVersion":"v1"}')
    signal = AnalysisSignal(evidenceComplete=True, fixCandidate=True)
    assert analyze_bug(cli, (), AnalysisPhase.FINAL, signal=signal) == analyze_bug(codex, (), AnalysisPhase.FINAL, signal=signal)
