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
    def test_navigation_evidence_gate_is_reachable_from_every_skill(self) -> None:
        reference = SKILL_ROOT / "references" / "web-urls.md"
        entrypoints = [
            *sorted((REPO_ROOT / "skills").glob("*/SKILL.md")),
            REPO_ROOT / "AGENTS.md",
            README,
            CURRENT,
            REPO_ROOT / "skills/zentao-bug-resolver/references/workflow.md",
            SKILL_ROOT / "references/api-v2/bugs.md",
        ]
        for path in entrypoints:
            with self.subTest(entrypoint=path.relative_to(REPO_ROOT).as_posix()):
                document = path.read_text(encoding="utf-8")
                links = re.findall(r"\[[^\]]+\]\(([^)]+web-urls\.md)\)", document)
                self.assertTrue(links, "对象链接输出必须引用统一证据合同")
                for link in links:
                    self.assertEqual(reference.resolve(), (path.parent / link).resolve())
                self.assertIn("不得仅凭 ID", document)
                self.assertIn("页面 URL：当前能力无法可靠生成/尚未验证", document)

    def test_navigation_contract_covers_issue_45_evidence_and_failure_scenarios(self) -> None:
        reference = SKILL_ROOT / "references" / "web-urls.md"
        self.assertTrue(reference.is_file(), "缺少对象 Web URL 证据合同")
        document = reference.read_text(encoding="utf-8")
        # These are Agent instruction checks, not a simulated URL verifier.
        sections = {
            "只有 ID": ("不生成", "bug-view", "bugID"),
            "历史示例": ("不是当前实例证据", "不改猜另一种路由"),
            "传统 query route": ("当前实例", "目标对象", "已验证"),
            "伪静态 rewrite route": ("当前实例", "目标对象", "已验证"),
            "HTTP 200 假成功": ("登录页", "首页", "404", "不能", "verified=true"),
            "子路径部署": ("/zentao/", "不得丢失", "部署前缀"),
            "无法验证": ("页面 URL：当前能力无法可靠生成/尚未验证", "候选格式（未验证）"),
            "用户已验证模板": ("当前实例", "当前请求", "不得", "跨实例", "逐页验证"),
        }
        for heading, anchors in sections.items():
            with self.subTest(scenario=heading):
                match = re.search(rf"^### {re.escape(heading)}\n(.*?)(?=^### |^## |\Z)", document, re.M | re.S)
                self.assertIsNotNone(match, f"缺少场景：{heading}")
                for anchor in anchors:
                    self.assertIn(anchor, match.group(1))
        for anchor in (
            "API / CLI", "URL/link", "来源", "富文本", "附件",
            "instance/base_url", "resource=bug", "id=<ID>",
            "bug view <id> --json", "resource fetch", "没有", "web-url",
        ):
            with self.subTest(boundary=anchor):
                self.assertIn(anchor, document)

    def test_current_contract_documents_plugin_clone_and_runtime_contract(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        for required in (
            "6 Skills",
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
            "zentao-batch-export",
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

    def test_batch_export_is_registered_across_current_documentation_surfaces(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        features = FEATURES.read_text(encoding="utf-8")
        for name, document in (("current contract", current), ("README", readme), ("features", features)):
            with self.subTest(document=name):
                self.assertIn("zentao-batch-export", document)
        for anchor in ("type:id", "resource fetch", "content.md", "manifest.json", "zentao-export-<timestamp>-<short-id>.zip"):
            self.assertIn(anchor, current)

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
