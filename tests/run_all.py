from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str]) -> bool:
    print(f"\n== {label} ==")
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        print(f"{label}: FAIL ({result.returncode})")
        return False
    print(f"{label}: PASS")
    return True


def main() -> int:
    python = sys.executable
    checks = [
        ("zentao API skill", [python, "skills/zentao/tests/run_all.py"]),
        ("zentao-statistics", [python, "-m", "unittest", "discover", "-s", "skills/zentao-statistics/tests", "-p", "test_*.py"]),
        ("zentao-personal", [python, "-m", "unittest", "discover", "-s", "skills/zentao-personal/tests", "-p", "test_*.py"]),
        ("zentao-project-management", [python, "-m", "unittest", "discover", "-s", "skills/zentao-project-management/tests", "-p", "test_*.py"]),
        ("zentao-bug-resolver", [python, "-m", "unittest", "discover", "-s", "skills/zentao-bug-resolver/tests", "-p", "test_*.py"]),
        ("repository smoke", [python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]),
    ]
    ok = all(run(label, command) for label, command in checks)
    print(f"\nRepository result: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
