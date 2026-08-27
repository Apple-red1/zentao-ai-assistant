from __future__ import annotations

import re
import unittest
from pathlib import Path

from ..support import SKILL_ROOT


REPO_ROOT = SKILL_ROOT.parents[1]
CURRENT = REPO_ROOT / "docs" / "current-contract.md"
HISTORICAL = SKILL_ROOT / "RULES.md"
README = REPO_ROOT / "README.md"
FEATURES = REPO_ROOT / "docs" / "features.md"


class CurrentContractDocumentationTest(unittest.TestCase):
    def test_current_contract_documents_plugin_clone_and_runtime_contract(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        for required in (
            "5 Skills",
            "CLAUDE.md / GEMINI.md",
            "plugin.json / .claude-plugin / .codex-plugin",
            "project/user scope",
            "~/.zentao-ai-assistant/config.env",
            "Claude Code verified gate",
            "Codex verified gate",
            "Gemini Plugin not v1",
            "Cursor/Copilot/VS Code unverified",
            "API v2",
            "120/120",
            "R0/R1/R2/R3",
            "UNKNOWN_WRITE_RESULT",
            "standard library only / no MCP",
        ):
            with self.subTest(anchor=required):
                self.assertIn(required, current)

    def test_current_contract_is_the_only_current_authority_marker(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        historical = HISTORICAL.read_text(encoding="utf-8")
        self.assertIn("CURRENT / 当前唯一权威入口", current)
        self.assertIn("ARCHIVED / 已归档", historical)
        self.assertIn("docs/current-contract.md", historical)
        self.assertNotIn("当前权威规则", historical)

        marked = []
        for path in REPO_ROOT.rglob("*.md"):
            if path == HISTORICAL:
                continue
            if "当前权威规则" in path.read_text(encoding="utf-8"):
                marked.append(path.relative_to(REPO_ROOT).as_posix())
        self.assertEqual([], marked)

    def test_current_contract_describes_multi_skill_capabilities(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        for required in (
            "120 个 ZenTao API v2 endpoint",
            "zentao-statistics",
            "zentao-personal",
            "zentao-project-management",
            "zentao_skill.public",
            ".tmp/zentao/auth/",
            "R3 delete",
            "--yes",
            "python tests/run_all.py",
            "python3 skills/zentao/tests/run_all.py",
            "Real API calls: 0",
            "official-contract.json",
            "zentao-21.7.8.json",
        ):
            self.assertIn(required, current)
        for stale in ("当前仓库仍存在旧形态", "不暴露 Bug 删除命令", "本轮明确延期", "产品边界是单一"):
            self.assertNotIn(stale, current)

    def test_bug_resolver_is_registered_across_current_documentation_surfaces(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        features = FEATURES.read_text(encoding="utf-8")
        for name, document in (("current contract", current), ("README", readme), ("features", features)):
            with self.subTest(document=name):
                self.assertIn("zentao-bug-resolver", document)
        self.assertIn("| `skills/zentao-bug-resolver/` |", current)

    def test_bug_resolver_contract_locks_read_only_r2_queue_and_evidence_boundaries(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        for anchor in (
            "`select`",
            "`snapshot`",
            "`compare`",
            "只读 facade",
            "zentao_skill.public",
            "不是新的 API endpoint",
            "ANALYZE_ONLY",
            "LOCAL_FIX_ALLOWED",
            "RESOLVE_R2_ALLOWED",
            "SOLVABLE",
            "UNCLEAR",
            "NO_CODE_EVIDENCE",
            "BLOCKED",
            "complete=false",
            "partial_failures",
            "unsupported_filters",
            "unavailable_fields",
            "pending_queue",
            "用户再次明确继续",
            "基础 `zentao` CLI",
            "不会自动 close",
            "standalone comment",
            "active Bug 单独转派",
            "不访问真实 ZenTao",
            "Real API calls: 0",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, current)

    def test_bug_resolver_summary_invariants_are_shared_by_user_docs(self) -> None:
        documents = {
            "README": README.read_text(encoding="utf-8"),
            "current contract": CURRENT.read_text(encoding="utf-8"),
            "features": FEATURES.read_text(encoding="utf-8"),
        }
        sections = {
            "README": ("Bug 证据驱动流程的确定性脚本入口为：", "详细自然语言边界"),
            "current contract": ("- `zentao-bug-resolver` 是第四个", "- R3 delete"),
            "features": ("## `zentao-bug-resolver`", None),
        }
        required = (
            "select", "snapshot", "compare", "只读", "pending_queue", "Agent",
            "facade", "bug resolve", "ANALYZE_ONLY", "LOCAL_FIX_ALLOWED",
            "RESOLVE_R2_ALLOWED", "SOLVABLE", "UNCLEAR", "NO_CODE_EVIDENCE", "BLOCKED",
        )
        for name, document in documents.items():
            start, end = sections[name]
            start_at = document.index(start)
            section = document[start_at:document.index(end, start_at) if end else None]
            with self.subTest(document=name):
                for anchor in required:
                    self.assertIn(anchor, section)
                self.assertIsNotNone(re.search(r"select.*snapshot.*compare", section, re.S))
                self.assertIn("只读", section)
                self.assertIsNotNone(re.search(r"pending_queue.*不(?:会)?自动继续", section, re.S))
                self.assertIsNotNone(re.search(r"回到基础 `zentao` CLI", section, re.S))
                self.assertIsNotNone(re.search(r"不是(?:新的)? API endpoint.*120", section, re.S))
                self.assertIsNotNone(re.search(r"ANALYZE_ONLY.*LOCAL_FIX_ALLOWED.*RESOLVE_R2_ALLOWED", section, re.S))
                self.assertIsNotNone(re.search(r"SOLVABLE.*UNCLEAR.*NO_CODE_EVIDENCE.*BLOCKED", section, re.S))
                self.assertIn("Real API calls: 0", document)
                self.assertTrue(
                    "不是新的 API endpoint" in document or "不是 API endpoint" in document
                )

    def test_human_attested_path_is_propagated_without_weakening_ordinary_path(self) -> None:
        for relative in ("AGENTS.md", "README.md", "docs/current-contract.md", "docs/features.md", "docs/security.md", "docs/architecture.md", "docs/testing.md"):
            document = (REPO_ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(document=relative):
                for anchor in ("HUMAN_ATTESTED_RESOLVE", "trunk", "普通", "只读", "回读"):
                    self.assertIn(anchor, document)
                self.assertNotIn("默认不传 `--resolved-build`", document)


if __name__ == "__main__":
    unittest.main()
