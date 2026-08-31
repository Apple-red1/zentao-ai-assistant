from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit


class _FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.form_action: str | None = None
        self.hidden_fields: list[tuple[str, str]] = []
        self.uid_values: list[str] = []
        self.uid_invalid = False
        self._in_form = False
        self._found_form = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs}
        normalized_tag = tag.lower()
        if normalized_tag == "form" and not self._found_form:
            self._found_form = True
            self._in_form = True
            self.form_action = attributes.get("action")
            return
        if normalized_tag != "input" or not self._in_form:
            return
        name = attributes.get("name")
        input_type = (attributes.get("type") or "text").lower()
        value = attributes.get("value") or ""
        if name and input_type == "hidden":
            self.hidden_fields.append((name, attributes.get("value") or ""))
        # ZenTao 21.7.8 can render the editor uid as a text input. Only the
        # exact uid field is admitted; other visible controls never enter the
        # parsed form payload.
        if name == "uid" and input_type in {"hidden", "text"}:
            self.uid_values.append(value)
        elif name == "uid":
            self.uid_invalid = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form" and self._in_form:
            self._in_form = False


def parse_form(body: bytes) -> Any | None:
    from .legacy import LegacyForm

    parser = _FormParser()
    try:
        parser.feed(body.decode("utf-8", errors="replace"))
        parser.close()
    except Exception:
        return None
    if not parser._found_form:
        return None
    return LegacyForm(
        parser.form_action,
        tuple(parser.hidden_fields),
        tuple(parser.uid_values),
        parser.uid_invalid,
    )


def is_bug_form(form: Any, expected_url: str, *, form_kind: str) -> bool:
    if not form.action or form_kind not in {"create", "edit"}:
        return False
    try:
        action = urljoin(expected_url, form.action)
        from .legacy import _origin
        if _origin(action) != _origin(expected_url):
            return False
    except ValueError:
        return False
    parsed = urlsplit(action)
    query = parse_qs(parsed.query)
    expected_query = parse_qs(urlsplit(expected_url).query)
    identity = "productID" if form_kind == "create" else "bugID"
    return (
        parsed.path == urlsplit(expected_url).path
        and query.get("m") == ["bug"]
        and query.get("f") == [form_kind]
        and (identity not in query or query.get(identity) == expected_query.get(identity))
    )


def is_bug_edit_form(form: Any, expected_url: str) -> bool:
    return is_bug_form(form, expected_url, form_kind="edit")


def validate_bug_form_url(value: str, base_url: str) -> None:
    try:
        resolved = urljoin(base_url.rstrip("/") + "/", value)
        from .legacy import _origin
        if _origin(resolved) != _origin(base_url):
            raise ValueError("Bug 步骤图片 referer 必须与 ZenTao 页面同源")
        parsed = urlsplit(resolved)
        query = parse_qs(parsed.query)
    except ValueError as exc:
        if str(exc).startswith("Bug 步骤图片 referer"):
            raise
        raise ValueError("Bug 步骤图片 referer URL 无效") from exc
    if parsed.path != "/index.php" or query.get("m") != ["bug"] or query.get("f") not in (["create"], ["edit"]):
        raise ValueError("Bug 步骤图片 referer 必须是固定 Bug 表单")
