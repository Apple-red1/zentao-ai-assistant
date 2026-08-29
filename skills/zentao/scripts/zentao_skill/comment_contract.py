"""Static standalone-comment capability contract shared by all entry points."""

from __future__ import annotations


COMMENT_CAPABILITIES: dict[str, frozenset[str]] = {
    "bug": frozenset({"comment", "attachments", "inline_image"}),
    "story": frozenset({"comment", "attachments", "inline_image"}),
    "product": frozenset({"comment", "attachments", "inline_image"}),
    "task": frozenset({"comment", "attachments", "inline_image"}),
    "execution": frozenset({"comment", "attachments", "inline_image"}),
    "project": frozenset({"comment", "attachments", "inline_image"}),
    "test-task": frozenset({"comment", "attachments", "inline_image"}),
    "product-plan": frozenset({"comment", "attachments", "inline_image"}),
    "release": frozenset({"comment", "attachments", "inline_image"}),
    "build": frozenset({"comment", "attachments", "inline_image"}),
}

VERIFIED_COMMENT_RESOURCE_TYPES = frozenset({"bug", "story"})

# ZenTao's page protocol uses the historical resource names for these two
# modules even though the CLI keeps the hyphenated names used by the API
# surface.  Keep this mapping fixed; callers must not accept arbitrary query
# values from user input.
WEB_OBJECT_TYPES = {
    "test-task": "testtask",
    "product-plan": "productplan",
}


def web_object_type(resource: str) -> str:
    return WEB_OBJECT_TYPES.get(resource, resource)


def canonical_object_type(value: object) -> str:
    text = str(value or "")
    for resource, web_name in WEB_OBJECT_TYPES.items():
        if text == web_name:
            return resource
    return text


def is_allowed(resource: str, capability: str) -> bool:
    return capability in COMMENT_CAPABILITIES.get(resource, frozenset())
