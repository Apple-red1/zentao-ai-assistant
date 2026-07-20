#!/usr/bin/env python3
import shutil
import subprocess
import sys

COMMAND = ("zentao-ai-repository",)
executable = shutil.which(COMMAND[0])
if executable is None:
    raise SystemExit('Install the CLI with: pipx install "git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source". See docs/plugin-installation.md.')
raise SystemExit(subprocess.call([executable, *COMMAND[1:], *sys.argv[1:]]))
