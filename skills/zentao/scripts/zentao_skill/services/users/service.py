from __future__ import annotations

from pathlib import Path

from ...internal.errors import UsageError
from ...internal.zentao.users import UsersAPI


class UsersService:
    ENDPOINT_IDS = UsersAPI.ENDPOINT_IDS

    def __init__(self, api: UsersAPI) -> None:
        self.api = api

    def create(self, *, account: object | None, password: object | None, realname: object | None, vision: list[object] | None = None) -> object | None:
        return self.api.create(account=account, realname=realname, password=password, vision=vision)

    def edit(self, *, account: object | None, item_id: int, dept: object | None = None, email: object | None = None, group: list[object] | None = None, join: object | None = None, mobile: object | None = None, password: object | None = None, realname: object | None = None, vision: list[object] | None = None, weixin: object | None = None) -> object | None:
        if realname is None and dept is None and join is None and group is None and email is None and vision is None and mobile is None and weixin is None and password is None:
            raise UsageError("edit 至少需要提供一个修改字段")
        return self.api.edit(item_id=item_id, account=account, realname=realname, dept=dept, join=join, group=group, email=email, vision=vision, mobile=mobile, weixin=weixin, password=password)

    def list(self, *, browse: object | None = None, filters: object | None = None, group_join: object | None = None, order: str | None = None, page: object | None = None, per_page: object | None = None, sort: str | None = None) -> object | None:
        return self.api.list(browse=browse, sort=sort, order=order, per_page=per_page, page=page, filters=filters, group_join=group_join)

    def view(self, *, item_id: int) -> object | None:
        return self.api.view(item_id=item_id)

    def delete(self, *, item_id: int) -> object | None:
        return self.api.delete(item_id=item_id)
