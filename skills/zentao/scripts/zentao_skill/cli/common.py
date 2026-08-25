
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..internal.errors import UsageError


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return number


def page_int(value: str) -> int:
    number = positive_int(value)
    return number


def per_page_int(value: str) -> int:
    number = positive_int(value)
    if number > 1000:
        raise argparse.ArgumentTypeError("不能大于 1000")
    return number


def number(value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是数字") from exc


def auto_value(value: str) -> object:
    stripped = value.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise argparse.ArgumentTypeError("复杂数组值必须是有效 JSON") from exc
    if stripped.isdigit():
        return int(stripped)
    return value


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", dest="json_output", help="只输出机器可读 JSON")


def read_text_file(path: str | None) -> str | None:
    if path is None:
        return None
    target = Path(path)
    if not target.is_file():
        raise UsageError(f"文本文件不存在: {target}")
    return target.read_text(encoding="utf-8")


def resolve_text(args: argparse.Namespace, dest: str) -> object | None:
    value = getattr(args, dest, None)
    file_value = getattr(args, dest + "_file", None)
    if file_value is not None:
        return read_text_file(file_value)
    return value


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)
