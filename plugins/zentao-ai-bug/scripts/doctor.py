#!/usr/bin/env python3
import sys
try:
    from zentao_ai.cli.app import main
except ModuleNotFoundError as exc:
    if exc.name and exc.name.startswith("zentao_ai"):
        raise SystemExit('Install the CLI with: pipx install "git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source". See docs/plugin-installation.md.') from exc
    raise

sys.argv.insert(1, "doctor")
main()
