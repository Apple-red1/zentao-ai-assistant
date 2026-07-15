"""Command-line adapter for the deterministic report renderer."""

from __future__ import annotations

import argparse
import json
import sys

from .models import ReportError, require_mapping
from .renderer import render_personal, render_team


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("personal", "team"))
    return parser


def main() -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = _parser().parse_args()
    try:
        payload = require_mapping(json.load(sys.stdin), "payload")
        output = render_personal(payload) if args.mode == "personal" else render_team(payload)
    except (json.JSONDecodeError, ReportError) as error:
        print(str(error), file=sys.stderr)
        return 2
    sys.stdout.write(output)
    return 0
