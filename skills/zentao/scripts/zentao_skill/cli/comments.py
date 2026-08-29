from __future__ import annotations

import argparse
from pathlib import Path

from ..comment_contract import COMMENT_CAPABILITIES
from ..internal.errors import UsageError
from .common import add_json_flag, non_empty_text, positive_int, resolve_text


ENDPOINT_IDS = frozenset()


def register_comment_action(
    resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    *,
    resource: str,
) -> None:
    parser = resource_subparsers.add_parser("comment", help="追加独立评论（不改变对象生命周期）")
    parser.add_argument("id", type=positive_int, help="资源 ID")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--comment", type=non_empty_text, dest="comment", help="评论正文")
    group.add_argument("--comment-file", dest="comment_file", help="从 UTF-8 文件读取评论正文")
    if "attachments" in COMMENT_CAPABILITIES.get(resource, frozenset()):
        parser.add_argument("--file", action="append", dest="files", help="评论普通附件（可重复）")
    if "inline_image" in COMMENT_CAPABILITIES.get(resource, frozenset()):
        parser.add_argument("--inline-image", action="append", dest="inline_images", help="评论内嵌图片（可重复）")
    add_json_flag(parser)
    parser.set_defaults(_handler=_run_comment, _comment_resource=resource)


def _run_comment(services: object, args: argparse.Namespace) -> object:
    comment = resolve_text(args, "comment")
    if not isinstance(comment, str):
        raise UsageError("评论正文不能为空")
    service = getattr(services, "comments")
    return service.add(
        resource=args._comment_resource,
        object_id=args.id,
        comment=comment,
        files=tuple(Path(value) for value in (getattr(args, "files", None) or ())),
        inline_images=tuple(Path(value) for value in (getattr(args, "inline_images", None) or ())),
    )
