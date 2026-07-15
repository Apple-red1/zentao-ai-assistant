#!/usr/bin/env python3
try:
    from zentao_ai.reporting.cli import main
except ModuleNotFoundError as exc:
    if exc.name and exc.name.startswith("zentao_ai"):
        raise SystemExit("Clone the repository, then run: pipx install . from the repository root. See docs/plugin-installation.md.") from exc
    raise

raise SystemExit(main())
