#!/usr/bin/env python3
try:
    from zentao_ai.reporting.cli import main
except ModuleNotFoundError as exc:
    if exc.name and exc.name.startswith("zentao_ai"):
        raise SystemExit('Install the CLI with: pipx install "git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source". See docs/plugin-installation.md.') from exc
    raise

raise SystemExit(main())
