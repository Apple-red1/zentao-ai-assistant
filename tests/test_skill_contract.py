import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "zentao-ai-bug" / "skills" / "zentao-ai-bug"


class SkillContractTests(unittest.TestCase):
    def test_summary_owns_the_v2_personal_and_team_shapes(self):
        summary = (SKILL_ROOT / "bug-summary.md").read_text(encoding="utf-8")
        self.assertIn("模板版本：v2", summary)
        self.assertIn("## 等待补充信息 Bug", summary)
        self.assertIn("## 人工需走查 Bug", summary)
        self.assertIn("# 团队 Bug 汇总", summary)
        self.assertIn("| 成员 | 未关闭候选 | P1 | 7天以上无活动 |", summary)
        self.assertNotIn("## AI已分析 Bug", summary)
        self.assertNotIn("## 未处理 Bug", summary)
        self.assertNotIn("# 团队 Bug 日报", summary)

    def test_workflows_read_mode_specific_scopes_and_keep_team_candidates(self):
        personal = (SKILL_ROOT / "personal-bug-agent.md").read_text(encoding="utf-8")
        team = (SKILL_ROOT / "team-bug-report.md").read_text(encoding="utf-8")
        root = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("personal.scopeNames", personal)
        self.assertIn("team.scopeNames", team)
        self.assertIn("未关闭候选", team)
        self.assertIn("范围字段为空", team)
        self.assertIn("scripts/render-report.py", root)
        self.assertIn("templateVersion=v2", root)


if __name__ == "__main__":
    unittest.main()
