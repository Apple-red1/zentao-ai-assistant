from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import UsageError
from .common import compact_dict, endpoint, make_order_by, map_enum, validate_pagination
from .session import ZentaoSession


class FilesAPI:
    ENDPOINT_IDS = frozenset({'file.delete', 'file.upload', 'file.edit'})

    def __init__(self, session: ZentaoSession) -> None:
        self.session = session

    @endpoint('file.upload')
    def upload(self, *, file: str | Path, object_id: object | None, object_type: object | None) -> object | None:
        multipart = compact_dict({
            'file': file,
            'objectType': object_type,
            'objectID': object_id,
        })
        return self.session.post('/files', multipart=multipart)

    @endpoint('file.edit')
    def edit(self, *, file_name: object | None, item_id: int) -> object | None:
        body = compact_dict({
            'fileName': map_enum('fileName', file_name),
        })
        return self.session.put(f'/files/{item_id}', body=body)

    @endpoint('file.delete')
    def delete(self, *, item_id: int) -> object | None:
        result = self.session.delete(f'/files/{item_id}')
        return result if result is not None else {"status": "success", "id": item_id}
