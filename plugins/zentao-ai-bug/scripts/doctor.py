#!/usr/bin/env python3
import sys
try:
    from zentao_ai.cli.app import main
except ModuleNotFoundError as exc:
    if exc.name and exc.name.startswith("zentao_ai"):
        raise SystemExit("zentao-ai-assistant is not installed; run: pipx install zentao-ai-assistant") from exc
    raise

sys.argv.insert(1, "doctor")
main()
