from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from ..support import SKILL_ROOT


PRODUCTION_ROOT = SKILL_ROOT / "scripts"
REPOSITORY_ROOT = SKILL_ROOT.parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_runtime_and_tests_use_only_python_standard_library(self) -> None:
        allowed_local = {"zentao_skill", "tests"}
        third_party: list[tuple[Path, str]] = []
        python_roots = (PRODUCTION_ROOT, SKILL_ROOT / "tests")
        for python_root in python_roots:
            for path in python_root.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        names = [alias.name.split(".", 1)[0] for alias in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                        names = [node.module.split(".", 1)[0]]
                    else:
                        continue
                    for name in names:
                        if name not in sys.stdlib_module_names and name not in allowed_local:
                            third_party.append((path.relative_to(REPOSITORY_ROOT), name))
        self.assertEqual([], third_party)

    def test_layering_keeps_http_protocol_out_of_cli_and_services(self) -> None:
        forbidden = ("urllib", "/api.php/v2", "HttpClient", "urlopen(")
        violations: list[tuple[str, str]] = []
        for area in (PRODUCTION_ROOT / "zentao_skill" / "cli", PRODUCTION_ROOT / "zentao_skill" / "services"):
            for path in area.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    if token in text:
                        violations.append((str(path.relative_to(REPOSITORY_ROOT)), token))
        self.assertEqual([], violations)

    def test_project_tmp_directory_is_git_ignored(self) -> None:
        gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".tmp/", gitignore)

    def test_old_mcp_and_standalone_package_are_removed(self) -> None:
        self.assertFalse((REPOSITORY_ROOT / "src" / "zentao_ai").exists())
        self.assertFalse((REPOSITORY_ROOT / "plugins").exists())
        self.assertFalse((REPOSITORY_ROOT / "pyproject.toml").exists())
        self.assertFalse(any(REPOSITORY_ROOT.rglob(".mcp.json")))

    def test_production_file_size_limits_and_lightweight_skill(self) -> None:
        entry = SKILL_ROOT / "scripts" / "zentao.py"
        self.assertLess(len(entry.read_text(encoding="utf-8").splitlines()), 50)
        oversized = []
        for path in PRODUCTION_ROOT.rglob("*.py"):
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines >= 500:
                oversized.append((str(path.relative_to(REPOSITORY_ROOT)), lines))
        self.assertEqual([], oversized)

        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill_text.splitlines()), 100)
        # Full endpoint parameter contracts belong in references/CLI help, not SKILL.md.
        self.assertNotIn("bug.create", skill_text)
        self.assertNotIn("--affected-build", skill_text)

    def test_test_sources_only_name_loopback_http_endpoints(self) -> None:
        urls: list[tuple[str, str]] = []
        for path in (SKILL_ROOT / "tests").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for url in re.findall(r"https?://[^\s\"']+", text):
                if "{" in url:
                    continue
                urls.append((str(path.relative_to(REPOSITORY_ROOT)), url))
                host = urlsplit(url).hostname
                self.assertIn(host, {"127.0.0.1", "localhost"}, (path, url))
        self.assertTrue(urls, "测试必须显式包含本地 Fake/loopback 网络边界")


if __name__ == "__main__":
    unittest.main()
