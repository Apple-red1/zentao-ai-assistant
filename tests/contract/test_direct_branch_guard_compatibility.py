import json
import subprocess
import sys
from pathlib import Path


def test_preflight_keeps_json_fields_and_failure_exit_code(tmp_path: Path):
    script = Path(__file__).parents[2] / "scripts" / "direct-branch-guard.py"
    scope = {"repository": "example", "path": str(tmp_path / "missing"), "targetBranch": "main", "testCommands": ["pytest"]}
    result = subprocess.run([sys.executable, str(script), "preflight", "--config", str(tmp_path / "unused.yaml"), "--scope-json", json.dumps(scope)], text=True, capture_output=True)
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert {"allowed", "reasons", "repository", "path", "branch", "head", "ahead", "behind", "testCommands"} <= payload.keys()
