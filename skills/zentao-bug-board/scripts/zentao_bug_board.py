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
from board import TZ, collect_board, render_board, resolve_target  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="单个 ZenTao Project 或 Product 的 16:00 Bug 评审表（只读）")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--project", type=int, help="已唯一确认的 ZenTao Project ID")
    target.add_argument("--product", type=int, help="已唯一确认的 ZenTao Product ID")
    target.add_argument("--name", help="精确的 Project/Product 名称；允许省略末尾的“项目”口语后缀")
    parser.add_argument("--json", action="store_true", help="输出机器 JSON；默认输出 Markdown 表格")
    args = parser.parse_args(argv)
    if args.project is not None and args.project <= 0:
        parser.error("--project 必须是正整数")
    if args.product is not None and args.product <= 0:
        parser.error("--product 必须是正整数")
    try:
        client = get_client()
        if args.name is not None:
            scope, scope_id = resolve_target(client, args.name)
        elif args.product is not None:
            scope, scope_id = "product", args.product
        else:
            scope, scope_id = "project", args.project
        report = collect_board(client, scope_id, datetime.now(TZ), scope=scope)
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
