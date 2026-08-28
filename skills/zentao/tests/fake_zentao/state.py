
from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Any


class FakeState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._fixture = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "base_state.json").read_text(encoding="utf-8"))
        self.faults: dict[str, list[str]] = {}
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.resources = copy.deepcopy(self._fixture)
            self.next_id = 100
            self.next_action_id = 1000
            self.next_file_id = 5000
            self.requests: list[dict[str, Any]] = []
            self.faults = {}
            self.web_faults: dict[str, list[str]] = {}
            self.binary_resources: dict[str, dict[str, object]] = {}
            self.redirects: dict[str, str] = {}

    def plan_faults(self, endpoint_id: str, *faults: str) -> None:
        self.faults[endpoint_id] = list(faults)

    def next_fault(self, endpoint_id: str) -> str | None:
        values = self.faults.get(endpoint_id, [])
        return values.pop(0) if values else None

    def plan_web_faults(self, stage: str, *faults: str) -> None:
        self.web_faults[stage] = list(faults)

    def next_web_fault(self, stage: str) -> str | None:
        values = self.web_faults.get(stage, [])
        return values.pop(0) if values else None

    def record(self, value: dict[str, Any]) -> None:
        with self._lock:
            self.requests.append(copy.deepcopy(value))

    def add_binary(self, path: str, content: bytes, *, content_type: str = "application/octet-stream", filename: str | None = None) -> None:
        self.binary_resources[path] = {"content": bytes(content), "content_type": content_type, "filename": filename}

    def add_redirect(self, path: str, location: str) -> None:
        self.redirects[path] = location

    def add_comment(
        self,
        *,
        resource: str,
        object_id: int,
        comment: str,
        files: list[dict[str, object]] | None = None,
        actor: str = "admin",
    ) -> dict[str, object]:
        with self._lock:
            action_id = self.next_action_id
            self.next_action_id += 1
            action_files: list[dict[str, object]] = []
            for file_entry in files or []:
                file_id = self.next_file_id
                self.next_file_id += 1
                name = str(file_entry["name"])
                content = bytes(file_entry.get("content", b""))
                path = f"/comment-files/{file_id}"
                self.add_binary(path, content, content_type=str(file_entry.get("content_type") or "application/octet-stream"), filename=name)
                action_files.append({
                    "id": file_id,
                    "fileID": file_id,
                    "objectType": "comment",
                    "objectID": action_id,
                    "title": name,
                    "name": name,
                    "size": len(content),
                    "url": path,
                })
            action: dict[str, object] = {
                "id": action_id,
                "action": "commented",
                "objectType": resource,
                "objectID": object_id,
                "actor": actor,
                "account": actor,
                "comment": comment,
            }
            if action_files:
                action["files"] = action_files
            bucket = self.resources.setdefault(resource, {})
            item = bucket.setdefault(str(object_id), {"id": object_id, "status": "active"})
            actions = item.setdefault("actions", [])
            if not isinstance(actions, list):
                actions = []
                item["actions"] = actions
            actions.append(action)
            return copy.deepcopy(action)

    def add_inline_image(self, content: bytes, *, filename: str = "inline.png", content_type: str = "image/png") -> tuple[int, str]:
        with self._lock:
            file_id = self.next_file_id
            self.next_file_id += 1
            self.add_binary("/index.php", content, content_type=content_type, filename=filename)
            return file_id, f"/index.php?m=file&f=read&t=png&fileID={file_id}"

    def handle(self, route: object, path_params: dict[str, int], query: dict[str, Any], body: dict[str, Any]) -> tuple[int, object | None]:
        endpoint_id = getattr(route, "endpoint_id")
        resource = getattr(route, "resource")
        operation = getattr(route, "operation")
        if endpoint_id == "token.login":
            if not body.get("account") or not body.get("password"):
                return 401, {"error": "invalid credentials"}
            return 200, {"status": "success", "token": "fake-token"}
        bucket = self.resources.setdefault(resource, {})
        item_id = next((v for k, v in path_params.items() if k.lower().endswith("id") and k.lower() not in {"productid", "projectid", "executionid", "programid"}), None)
        if endpoint_id in {"release.create", "release.edit"} and body.get("status") == "normal" and not body.get("releasedDate"):
            return 200, {"status": "fail", "message": {"releasedDate": ["『实际发布日期』不能为空。"]}}
        if operation == "create" or operation == "upload":
            ident = self.next_id; self.next_id += 1
            item = {"id": ident, **body, "status": body.get("status", "active")}
            bucket[str(ident)] = item
            return 200, copy.deepcopy(item)
        if operation == "edit" or operation == "change":
            ident = item_id or next(iter(path_params.values()), 1)
            item = bucket.setdefault(str(ident), {"id": ident, "status": "active"})
            item.update(body)
            if operation == "change": item["version"] = int(item.get("version", 1)) + 1
            return 200, copy.deepcopy(item)
        if operation.startswith("list"):
            rows = list(bucket.values())
            # Minimal scope filter based on path params.
            for key, value in path_params.items():
                field = key.removesuffix("ID")
                filtered = [row for row in rows if row.get(key) == value or row.get(field) == value]
                if filtered:
                    rows = filtered
            page = int(query.get("pageID", 1)); per_page = int(query.get("recPerPage", 100))
            start = (page - 1) * per_page
            key = resource.replace("-", "") + "s"
            return 200, {key: copy.deepcopy(rows[start:start+per_page]), "pager": {"pageID": page, "recPerPage": per_page, "total": len(rows)}}
        if operation == "view":
            ident = item_id or next(iter(path_params.values()), 1)
            item = bucket.get(str(ident))
            return (200, copy.deepcopy(item)) if item else (404, {"error": "not found"})
        if operation in {"resolve", "close", "activate", "start", "finish"}:
            ident = item_id or next(iter(path_params.values()), 1)
            item = bucket.setdefault(str(ident), {"id": ident})
            status = {"resolve": "resolved", "close": "closed", "activate": "active", "start": "doing", "finish": "done"}[operation]
            item.update(body); item["status"] = status
            return 200, copy.deepcopy(item)
        if operation == "delete":
            ident = item_id or next(iter(path_params.values()), 1)
            bucket.pop(str(ident), None)
            if endpoint_id == "file.delete":
                return 200, {"status": "success", "id": ident}
            return 204, None
        return 500, {"error": "unhandled operation", "endpoint": endpoint_id}
