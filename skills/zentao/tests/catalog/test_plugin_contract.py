from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from ..support import SKILL_ROOT


REPOSITORY_ROOT = SKILL_ROOT.parents[1]
PORTABLE_MANIFEST = REPOSITORY_ROOT / "plugin.json"
CLAUDE_ROOT = REPOSITORY_ROOT / ".claude-plugin"
CLAUDE_MANIFEST = CLAUDE_ROOT / "plugin.json"
CLAUDE_MARKETPLACE = CLAUDE_ROOT / "marketplace.json"
CODEX_ROOT = REPOSITORY_ROOT / ".codex-plugin"
CODEX_MANIFEST = CODEX_ROOT / "plugin.json"
CODEX_MARKETPLACE = REPOSITORY_ROOT / ".agents" / "plugins" / "marketplace.json"
PUBLIC_SKILLS = (
    "zentao",
    "zentao-statistics",
    "zentao-personal",
    "zentao-project-management",
    "zentao-bug-resolver",
    "zentao-batch-export",
)
PORTABLE_MANIFEST_FIELDS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}
PLUGIN_NAME = "zentao-ai-assistant"
PLUGIN_VERSION = "1.2.0"
PLUGIN_DESCRIPTION = "ZenTao project management skills for AI coding agents."
PLUGIN_REPOSITORY_PATH = "Apple-red1/zentao-ai-assistant"
PLUGIN_SCHEMA = "https" + "://agent-" + "plugins.org/schemas/1.0.0/plugin.schema.json"


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return value


class PluginContractTests(unittest.TestCase):
    def test_portable_manifest_is_the_single_closed_core_manifest(self) -> None:
        manifest = read_json(PORTABLE_MANIFEST)
        self.assertTrue(set(manifest) <= PORTABLE_MANIFEST_FIELDS)
        self.assertEqual(PLUGIN_SCHEMA, manifest["$schema"])
        self.assertEqual(PLUGIN_NAME, manifest["name"])
        self.assertEqual(PLUGIN_VERSION, manifest["version"])
        self.assertEqual(PLUGIN_DESCRIPTION, manifest["description"])
        self.assertEqual(PLUGIN_REPOSITORY_PATH, urlsplit(manifest["repository"]).path.strip("/"))
        self.assertEqual("MIT", manifest["license"])

    def test_public_skill_surface_has_exactly_six_skills(self) -> None:
        skills_root = REPOSITORY_ROOT / "skills"
        immediate_skill_names = sorted(
            path.name for path in skills_root.iterdir() if path.is_dir()
        )
        self.assertEqual(sorted(PUBLIC_SKILLS + ("_shared",)), immediate_skill_names)
        for skill_name in PUBLIC_SKILLS:
            with self.subTest(skill=skill_name):
                self.assertTrue((skills_root / skill_name / "SKILL.md").is_file())
        self.assertFalse((skills_root / "_shared" / "SKILL.md").exists())

    def test_claude_manifest_matches_portable_identity_without_non_skill_components(self) -> None:
        manifest = read_json(CLAUDE_MANIFEST)
        self.assertEqual(PLUGIN_NAME, manifest["name"])
        self.assertEqual(PLUGIN_VERSION, manifest["version"])
        self.assertEqual(PLUGIN_DESCRIPTION, manifest["description"])
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn("commands", manifest)
        self.assertNotIn("agents", manifest)
        self.assertNotIn("hooks", manifest)
        self.assertNotIn("skills", manifest)
        self.assertFalse((CLAUDE_ROOT / "skills").exists())

    def test_claude_marketplace_has_one_root_plugin_entry(self) -> None:
        marketplace = read_json(CLAUDE_MARKETPLACE)
        self.assertEqual(PLUGIN_NAME, marketplace["name"])
        self.assertEqual("Apple-red1", marketplace["owner"]["name"])
        self.assertEqual(1, len(marketplace["plugins"]))
        entry = marketplace["plugins"][0]
        self.assertEqual(PLUGIN_NAME, entry["name"])
        self.assertEqual(".", entry["source"])
        self.assertNotIn("mcpServers", entry)

    def test_codex_manifest_points_at_the_canonical_skill_root(self) -> None:
        manifest = read_json(CODEX_MANIFEST)
        self.assertEqual({"name", "version", "description", "skills"}, set(manifest))
        self.assertEqual(PLUGIN_NAME, manifest["name"])
        self.assertEqual(PLUGIN_VERSION, manifest["version"])
        self.assertEqual(PLUGIN_DESCRIPTION, manifest["description"])
        self.assertEqual("./skills/", manifest["skills"])
        for forbidden in ("mcpServers", "apps", "hooks", "agents"):
            self.assertNotIn(forbidden, manifest)
        self.assertFalse((CODEX_ROOT / "skills").exists())

    def test_codex_marketplace_has_one_local_root_entry_with_policy(self) -> None:
        marketplace = read_json(CODEX_MARKETPLACE)
        self.assertEqual(PLUGIN_NAME, marketplace["name"])
        self.assertTrue(marketplace["interface"]["displayName"])
        self.assertEqual(1, len(marketplace["plugins"]))
        entry = marketplace["plugins"][0]
        self.assertEqual(PLUGIN_NAME, entry["name"])
        self.assertEqual({"source", "path"}, set(entry["source"]))
        self.assertEqual("local", entry["source"]["source"])
        self.assertEqual("./", entry["source"]["path"])
        self.assertEqual("AVAILABLE", entry["policy"]["installation"])
        self.assertEqual("ON_INSTALL", entry["policy"]["authentication"])
        self.assertEqual("Productivity", entry["category"])
        for forbidden in ("mcpServers", "apps", "hooks", "agents"):
            self.assertNotIn(forbidden, entry)


if __name__ == "__main__":
    unittest.main()
