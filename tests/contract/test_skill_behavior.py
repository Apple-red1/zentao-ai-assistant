from __future__ import annotations

from pathlib import Path

import yaml


SKILL_PATH = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "zentao-ai-bug"
    / "skills"
    / "zentao-ai-bug"
    / "SKILL.md"
)


def skill_parts() -> tuple[dict[str, str], str]:
    text = SKILL_PATH.read_text(encoding="utf-8")
    _, raw_frontmatter, body = text.split("---", 2)
    return yaml.safe_load(raw_frontmatter), body


def test_skill_frontmatter_is_discoverable_and_minimal() -> None:
    frontmatter, _ = skill_parts()

    assert frontmatter.keys() == {"name", "description"}
    assert frontmatter["name"] == "zentao-ai-bug"
    assert frontmatter["description"].startswith("Use when")
    assert "禅道" in frontmatter["description"]


def test_skill_routes_every_supported_intent() -> None:
    _, body = skill_parts()

    for tool in (
        "query_my_bugs",
        "query_team_bugs",
        "query_user_bugs",
        "search_bugs",
        "get_bug",
        "list_users",
        "add_bug_comment",
        "edit_bug",
        "activate_bug",
        "assign_bug",
    ):
        assert f"`{tool}`" in body


def test_skill_requires_current_message_confirmation_and_refuses_delete() -> None:
    _, body = skill_parts()
    normalized = body.casefold().replace(" ", "")

    assert "confirm:true" in normalized
    assert "当前消息" in body
    assert "永久拒绝" in body
    assert "删除" in body
