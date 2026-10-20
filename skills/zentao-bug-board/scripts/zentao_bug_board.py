#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED = REPO_ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.runtime import get_client  # noqa: E402
from board import TZ, collect_board, render_board  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="单个 ZenTao Project 的 16:00 Bug 评审表（只读）")
    parser.add_argument("--project", type=int, required=True, help="已唯一确认的 ZenTao Project ID")
    parser.add_argument("--json", action="store_true", help="输出机器 JSON；默认输出 Markdown 表格")
    args = parser.parse_args(argv)
    if args.project <= 0:
        parser.error("--project 必须是正整数")
    try:
        report = collect_board(get_client(), args.project, datetime.now(TZ))
    except Exception as exc:
        print(json.dumps({"error": {"code": "BUG_BOARD_ERROR", "message": str(exc), "details": {}}},
                         ensure_ascii=False), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    else:
        print(render_board(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
