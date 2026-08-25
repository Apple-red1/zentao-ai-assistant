from __future__ import annotations

import argparse

from ...services.resources.service import ResourcesService
from ..common import add_json_flag, positive_int


ENDPOINT_IDS = frozenset()


def register(resource_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = resource_subparsers.add_parser("fetch", help="获取对象附件区和富文本中的全部资源文件")
    parser.add_argument("--object-type", required=True, choices=sorted(ResourcesService.OBJECT_TYPES), dest="object_type")
    parser.add_argument("--object-id", required=True, type=positive_int, dest="object_id")
    add_json_flag(parser)
    parser.set_defaults(_handler=_run_fetch)


def _run_fetch(services: object, args: argparse.Namespace) -> object:
    service: ResourcesService = getattr(services, "resource")
    return service.fetch(object_type=args.object_type, object_id=args.object_id)
