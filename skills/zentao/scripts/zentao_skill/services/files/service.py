from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.files import FilesAPI


class FilesService:
    ENDPOINT_IDS = FilesAPI.ENDPOINT_IDS

    def __init__(self, api: FilesAPI) -> None:
        self.api = api

    def upload(self, *, file: str | Path, object_id: object | None, object_type: object | None) -> object | None:
        return self.api.upload(file=file, object_type=object_type, object_id=object_id)

    def edit(self, *, file_name: object | None, item_id: int) -> object | None:
        return self.api.edit(item_id=item_id, file_name=file_name)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
