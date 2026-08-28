from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from ..support import SKILL_ROOT


REPOSITORY_ROOT = SKILL_ROOT.parents[1]
PRODUCTION_ROOT = SKILL_ROOT / "scripts"
HIGH_LEVEL_SKILLS = (
    REPOSITORY_ROOT / "skills" / "zentao-statistics",
    REPOSITORY_ROOT / "skills" / "zentao-personal",
    REPOSITORY_ROOT / "skills" / "zentao-project-management",
    REPOSITORY_ROOT / "skills" / "zentao-bug-resolver",
    REPOSITORY_ROOT / "skills" / "zentao-batch-export",
)
SHARED_ROOT = REPOSITORY_ROOT / "skills" / "_shared" / "zentao"


class RepositoryContractTests(unittest.TestCase):
    def test_runtime_and_tests_use_only_python_standard_library(self) -> None:
        allowed_local = {"zentao_skill", "tests", "zentao", "resource_validation"}
        third_party: list[tuple[Path, str]] = []
        roots = [PRODUCTION_ROOT, SKILL_ROOT / "tests", SHARED_ROOT, REPOSITORY_ROOT / "tests"]
        for skill in HIGH_LEVEL_SKILLS:
            roots.extend([skill / "scripts", skill / "tests"])
        for python_root in roots:
            if not python_root.exists():
                continue
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

    def test_api_layering_keeps_http_protocol_out_of_cli_and_services(self) -> None:
        forbidden = ("urllib", "/api.php/v2", "HttpClient", "urlopen(")
        violations: list[tuple[str, str]] = []
        for area in (PRODUCTION_ROOT / "zentao_skill" / "cli", PRODUCTION_ROOT / "zentao_skill" / "services"):
            for path in area.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    if token in text:
                        violations.append((str(path.relative_to(REPOSITORY_ROOT)), token))
        self.assertEqual([], violations)

    def test_high_level_skills_use_public_facade_instead_of_http_or_internal(self) -> None:
        forbidden = ("urllib", "/api.php/v2", "zentao_skill.internal", "HttpClient", "urlopen(")
        violations = []
        areas = [SHARED_ROOT] + [skill / "scripts" for skill in HIGH_LEVEL_SKILLS]
        for area in areas:
            for path in area.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    if token in text:
                        violations.append((str(path.relative_to(REPOSITORY_ROOT)), token))
        self.assertEqual([], violations)
        self.assertTrue((PRODUCTION_ROOT / "zentao_skill" / "public" / "client.py").is_file())

    def test_expected_multi_skill_surface_exists(self) -> None:
        for skill in HIGH_LEVEL_SKILLS:
            with self.subTest(skill=skill.name):
                self.assertTrue((skill / "SKILL.md").is_file())
                self.assertTrue((skill / "agents" / "openai.yaml").is_file())
                self.assertTrue((skill / "scripts").is_dir())
        self.assertFalse((SHARED_ROOT / "SKILL.md").exists())

    def test_clone_instruction_routes_and_thin_bridges_preserve_canonical_rules(self) -> None:
        agents = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for skill_name in (
            "skills/zentao/",
            "skills/zentao-statistics/",
            "skills/zentao-personal/",
            "skills/zentao-project-management/",
            "skills/zentao-bug-resolver/",
            "skills/zentao-batch-export/",
        ):
            self.assertIn(skill_name, agents)
        routes = {
            "调查/修复/验证并可能 resolve Bug": "zentao-bug-resolver",
            "多个 ZenTao 对象的完整资料、附件打包下载": "zentao-batch-export",
            "Project/Execution 进度、健康、风险、工作量": "zentao-project-management",
            "自己/某人的待办、风险、工作摘要": "zentao-personal",
            "数量、分布、汇总、比较": "zentao-statistics",
            "原子 ZenTao read/write/lifecycle/delete/resource": "zentao",
        }
        for goal, skill_name in routes.items():
            with self.subTest(goal=goal):
                self.assertIn(goal, agents)
                self.assertIn(f"`{skill_name}`", agents)
        self.assertIn("选中后必须读取对应 `skills/<name>/SKILL.md`", agents)
        for contract in (
            "ZenTao API v2",
            "R0 Read",
            "R1 Normal Write",
            "R2 Lifecycle",
            "R3 delete",
            "UNKNOWN_WRITE_RESULT",
            "Python 版本为 3.11+",
            "Fake/真实 ZenTao",
            "python tests/run_all.py",
            "python skills/zentao/tests/run_all.py",
        ):
            self.assertIn(contract, agents)
        self.assertNotIn("skills/_shared/zentao/SKILL.md", agents)

        for bridge_name in ("CLAUDE.md", "GEMINI.md"):
            bridge = REPOSITORY_ROOT / bridge_name
            self.assertTrue(bridge.is_file())
            bridge_text = bridge.read_text(encoding="utf-8").strip()
            self.assertIn("@AGENTS.md", bridge_text)
            self.assertLessEqual(len(bridge_text.splitlines()), 3)
            self.assertNotIn("zentao-bug-resolver", bridge_text)
            self.assertNotIn("R0 Read", bridge_text)


    def test_project_tmp_directory_is_git_ignored(self) -> None:
        gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".tmp/", gitignore)

    def test_old_mcp_and_standalone_package_are_removed(self) -> None:
        self.assertFalse((REPOSITORY_ROOT / "src" / "zentao_ai").exists())
        self.assertFalse((REPOSITORY_ROOT / "plugins").exists())
        self.assertFalse((REPOSITORY_ROOT / "pyproject.toml").exists())
        self.assertFalse(any(REPOSITORY_ROOT.rglob(".mcp.json")))

    def test_production_file_size_limits_and_lightweight_api_skill(self) -> None:
        entry = SKILL_ROOT / "scripts" / "zentao.py"
        self.assertLess(len(entry.read_text(encoding="utf-8").splitlines()), 50)
        oversized = []
        for path in (REPOSITORY_ROOT / "skills").rglob("*.py"):
            if "/tests/" in path.as_posix():
                continue
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines >= 500:
                oversized.append((str(path.relative_to(REPOSITORY_ROOT)), lines))
        self.assertEqual([], oversized)

        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill_text.splitlines()), 100)
        self.assertNotIn("bug.create", skill_text)
        self.assertNotIn("--affected-build", skill_text)

    def test_test_sources_only_name_loopback_http_endpoints(self) -> None:
        urls: list[tuple[str, str]] = []
        for root in (SKILL_ROOT / "tests", REPOSITORY_ROOT / "tests"):
            for path in root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                for url in re.findall(r"https?://[^\s\"']+", text):
                    if "{" in url or "zentao.example.com" in url:
                        continue
                    urls.append((str(path.relative_to(REPOSITORY_ROOT)), url))
                    host = urlsplit(url).hostname
                    self.assertIn(host, {"127.0.0.1", "localhost"}, (path, url))
        self.assertTrue(urls, "测试必须显式包含本地 Fake/loopback 网络边界")


if __name__ == "__main__":
    unittest.main()
