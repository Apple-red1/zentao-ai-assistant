from __future__ import annotations

import contextlib
import io
import json
import runpy
import sys
from pathlib import Path

SKILL_ROOT=Path(__file__).resolve().parents[2]
SCRIPTS=SKILL_ROOT/"scripts"
CLI=SCRIPTS/"zentao.py"
if str(SCRIPTS) not in sys.path: sys.path.insert(0,str(SCRIPTS))


def invoke_entry(argv: list[str]) -> tuple[int, str, str]:
    stdout=io.StringIO(); stderr=io.StringIO(); previous=list(sys.argv)
    try:
        sys.argv=[str(CLI),*argv]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                runpy.run_path(str(CLI),run_name="__main__")
            except SystemExit as exc:
                code=0 if exc.code is None else int(exc.code)
            else:
                code=0
    finally:
        sys.argv=previous
    return code,stdout.getvalue(),stderr.getvalue()


def run() -> int:
    cases=json.load(sys.stdin)
    results=[]
    for case in cases:
        code,stdout,stderr=invoke_entry(list(case["argv"]))
        results.append({
            "endpoint_id":case["endpoint_id"],
            "returncode":code,
            "stdout":stdout,
            "stderr":stderr,
        })
    json.dump(results,sys.stdout,ensure_ascii=False,separators=(",",":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__": raise SystemExit(run())
