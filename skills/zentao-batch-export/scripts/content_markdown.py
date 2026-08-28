from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


_RICH_TEXT_TAG_RE = re.compile(
    r"<\s*/?\s*(?:a|br|div|img|li|p|pre|span|table|tbody|td|th|tr)\b",
    re.IGNORECASE,
)
_SRCSET_FIRST_RE = re.compile(r"\s*(data:\S+|[^\s,]+)")


def _escape_markdown_text(value: str) -> str:
    return re.sub(r"([\\`*_\[\]])", r"\\\1", value)


def _resource_path_for_source(source: object, resource_paths: dict[str, str]) -> str | None:
    if not isinstance(source, str) or not source:
        return None
    path = resource_paths.get(source)
    if path is not None:
        return path
    if source.startswith("data:"):
        for display_source, resource_path in resource_paths.items():
            if display_source.startswith("data:") and display_source.endswith(",..."):
                if source.startswith(display_source[:-3]):
                    return resource_path
    return None


def _replace_resource_references(value: str, resource_paths: dict[str, str]) -> str:
    result = value
    for source, path in sorted(resource_paths.items(), key=lambda item: len(item[0]), reverse=True):
        if source and not source.startswith("data:"):
            result = result.replace(source, path)
    return result


def _first_srcset_source(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = _SRCSET_FIRST_RE.match(value)
    return match.group(1) if match else None


class _RichTextMarkdownParser(HTMLParser):
    def __init__(self, resource_paths: dict[str, str]) -> None:
        super().__init__(convert_charrefs=True)
        self.resource_paths = resource_paths
        self.parts: list[str] = []
        self.links: list[str | None] = []

    def _append(self, value: str) -> None:
        if value:
            self.parts.append(value)

    def _newline(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def _destination(self, source: object) -> tuple[str, bool]:
        path = _resource_path_for_source(source, self.resource_paths)
        if path is not None:
            return path, True
        value = str(source or "")
        return value, value.startswith("resources/")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value for name, value in attrs if value is not None}
        tag = tag.lower()
        if tag == "img":
            source = values.get("src") or _first_srcset_source(values.get("srcset"))
            if source:
                destination, archived = self._destination(source)
                alt = values.get("alt", "").strip()
                if not alt or "index.php" in alt.lower() or "fileid=" in alt.lower():
                    alt = Path(destination).name or "image"
                if archived:
                    self._append(f"![{_escape_markdown_text(alt)}](<{destination}>)")
                else:
                    self._append(f"（图片未归档：{_escape_markdown_text(source)}）")
            return
        if tag == "a":
            self.links.append(values.get("href"))
            self._append("[")
        elif tag in {"br", "p", "div", "li", "tr"}:
            self._newline()
        elif tag in {"strong", "b"}:
            self._append("**")
        elif tag in {"em", "i"}:
            self._append("*")
        elif tag == "code":
            self._append("`")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a":
            href = self.links.pop() if self.links else None
            if href:
                destination, _ = self._destination(href)
                self._append(f"](<{destination}>)")
            else:
                self._append("]")
        elif tag in {"p", "div", "li", "tr"}:
            self._newline()
        elif tag in {"strong", "b"}:
            self._append("**")
        elif tag in {"em", "i"}:
            self._append("*")
        elif tag == "code":
            self._append("`")

    def handle_data(self, data: str) -> None:
        self._append(_escape_markdown_text(data))


def _render_rich_text(value: str, resource_paths: dict[str, str]) -> str:
    parser = _RichTextMarkdownParser(resource_paths)
    try:
        parser.feed(value)
        parser.close()
    except (AssertionError, ValueError):
        return _escape_markdown_text(value)
    return "".join(parser.parts).strip()


def _format_scalar(value: object, resource_paths: dict[str, str]) -> str:
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, (int, float)):
        return f"`{value}`"
    text = _replace_resource_references(str(value), resource_paths)
    if not text:
        return "（空字符串）"
    if _RICH_TEXT_TAG_RE.search(text):
        rendered = _render_rich_text(text, resource_paths)
        if rendered:
            return rendered
    if "\n" in text or "```" in text:
        fence = "`" * max(3, _longest_backtick_run(text) + 1)
        return f"{fence}text\n{text}\n{fence}"
    return _escape_markdown_text(text)


def _longest_backtick_run(text: str) -> int:
    longest = current = 0
    for char in text:
        if char == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _append_markdown_field(
    lines: list[str],
    indent: str,
    label: str,
    value: object,
    resource_paths: dict[str, str],
) -> None:
    formatted = _format_scalar(value, resource_paths)
    escaped_label = _escape_markdown_text(label)
    if "\n" not in formatted:
        lines.append(f"{indent}- **{escaped_label}**: {formatted}")
        return
    lines.append(f"{indent}- **{escaped_label}**:")
    lines.extend(f"{indent}  {line}" if line else f"{indent}  " for line in formatted.splitlines())


def _render_markdown_value(value: object, indent: str, resource_paths: dict[str, str]) -> list[str]:
    if isinstance(value, dict):
        if not value:
            return [f"{indent}（空对象）"]
        lines: list[str] = []
        for key, item in value.items():
            label = str(key)
            if isinstance(item, (dict, list)):
                if not item:
                    empty_label = "空对象" if isinstance(item, dict) else "空列表"
                    lines.append(f"{indent}- **{_escape_markdown_text(label)}**: （{empty_label}）")
                else:
                    lines.append(f"{indent}- **{_escape_markdown_text(label)}**:")
                    lines.extend(_render_markdown_value(item, indent + "  ", resource_paths))
            else:
                _append_markdown_field(lines, indent, label, item, resource_paths)
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{indent}（空列表）"]
        lines: list[str] = []
        for index, item in enumerate(value, start=1):
            label = f"第 {index} 项"
            if isinstance(item, (dict, list)):
                if not item:
                    empty_label = "空对象" if isinstance(item, dict) else "空列表"
                    lines.append(f"{indent}- **{label}**: （{empty_label}）")
                else:
                    lines.append(f"{indent}- **{label}**:")
                    lines.extend(_render_markdown_value(item, indent + "  ", resource_paths))
            else:
                _append_markdown_field(lines, indent, label, item, resource_paths)
        return lines
    return [f"{indent}{_format_scalar(value, resource_paths)}"]


def _render_markdown_document(payload: object, resource_paths: dict[str, str]) -> str:
    if not isinstance(payload, dict):
        return _format_scalar(payload, resource_paths) + "\n"
    lines: list[str] = []
    for key, value in payload.items():
        lines.extend([f"## {_escape_markdown_text(str(key))}", ""])
        lines.extend(_render_markdown_value(value, "", resource_paths))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_content_markdown(
    object_type: str,
    object_id: int,
    payload: object,
    resource_paths: dict[str, str] | None = None,
) -> str:
    resource_paths = resource_paths or {}
    return (
        f"# ZenTao {object_type}:{object_id}\n\n"
        f"> 数据来源：`zentao {object_type} view {object_id}`。"
        "以下为该 `view` 当前实际返回的完整字段，使用可读 Markdown 展示。\n\n"
        f"{_render_markdown_document(payload, resource_paths)}"
    )


def render_failed_content_markdown(object_type: str, object_id: int, failure: dict[str, object]) -> str:
    return (
        f"# ZenTao {object_type}:{object_id}\n\n"
        "> 对象详情读取失败，本文件只记录本次导出失败信息；完整失败清单同时保存在根目录 `manifest.json`。\n\n"
        f"## 失败信息\n\n{_render_markdown_document(failure, {})}"
    )
