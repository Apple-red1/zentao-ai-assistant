#!/usr/bin/env python3
try:
    from zentao_ai.reporting.cli import main
except ModuleNotFoundError as exc:
    if exc.name and exc.name.startswith("zentao_ai"):
        raise SystemExit("zentao-ai-assistant is not installed; run: pipx install zentao-ai-assistant") from exc
    raise

raise SystemExit(main())
