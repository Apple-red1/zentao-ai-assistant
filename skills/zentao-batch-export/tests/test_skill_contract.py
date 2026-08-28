from __future__ import annotations

import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
AGENT = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")


class BatchExportSkillContractTests(unittest.TestCase):
    def test_skill_declares_trigger_and_neighbor_boundaries(self) -> None:
        for anchor in (
            "多个 ZenTao 对象",
            "打包下载",
            "ordinary single-object view/query stays in zentao",
            "zentao-statistics",
            "zentao-bug-resolver",
        ):
            self.assertIn(anchor, SKILL)

    def test_skill_declares_supported_types_and_type_id_input(self) -> None:
        for object_type in (
            "bug", "epic", "execution", "feedback", "product", "product-plan", "program",
            "requirement", "story", "task", "test-case", "ticket", "user",
        ):
            self.assertIn(object_type, SKILL)
        self.assertIn("type + id", SKILL)
        self.assertIn("bug:123", SKILL)

    def test_skill_declares_complete_markdown_resources_manifest_and_failure_semantics(self) -> None:
        for anchor in (
            "完整 `content.md`",
            "resource fetch",
            "manifest.json",
            "单个对象详情、附件或富文本资源失败，不阻断后续对象",
            "complete",
            "failures",
            "不额外生成与 `content.md` 重复的 `data.json`",
        ):
            self.assertIn(anchor, SKILL)

    def test_skill_declares_safe_runtime_paths_and_dynamic_zip_name(self) -> None:
        self.assertIn(".tmp/zentao/zentao-batch-export/<run-id>/", SKILL)
        self.assertIn("~/.zentao-ai-assistant/tmp/zentao/zentao-batch-export/<run-id>/", SKILL)
        self.assertIn("zentao-export-<YYYYMMDD-HHMMSS>-<short-run-id>.zip", SKILL)
        self.assertIn("不接受任意输出路径", SKILL)
        self.assertIn("拒绝符号链接和目录逃逸", SKILL)

    def test_openai_metadata_routes_to_batch_export(self) -> None:
        self.assertIn("$zentao-batch-export", AGENT)
        self.assertIn("完整字段", AGENT)
        self.assertIn("ZIP", AGENT)


if __name__ == "__main__":
    unittest.main()
