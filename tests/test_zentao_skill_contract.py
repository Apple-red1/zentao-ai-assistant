import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "zentao-ai-bug" / "skills" / "zentao-ai-bug"


class ZentaoSkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.personal = (SKILL_ROOT / "personal-bug-agent.md").read_text(encoding="utf-8")
        cls.analysis = (SKILL_ROOT / "bug-analysis.md").read_text(encoding="utf-8")
        cls.summary = (SKILL_ROOT / "bug-summary.md").read_text(encoding="utf-8")
        cls.team = (SKILL_ROOT / "team-bug-report.md").read_text(encoding="utf-8")

    def test_failed_tests_retain_verified_postimage_for_human_validation(self):
        self.assertIn("PATCH_RETAINED_FOR_HUMAN_VALIDATION", self.personal)
        self.assertIn("HEAD、分支、暂存区和 AI postimage", self.personal)
        self.assertIn("测试或 lint 失败本身不得触发恢复 preimage", self.personal)
        self.assertNotIn("测试失败时，只在 HEAD/分支未变且文件仍等于 AI postimage 时恢复对应 preimage", self.personal)

    def test_failed_tests_never_authorize_success_claim_or_comment(self):
        self.assertIn("PATCH_RETAINED_FOR_HUMAN_VALIDATION", self.analysis)
        self.assertIn("不得返回 `FIX_CANDIDATE`", self.analysis)
        self.assertIn("等待人工验证", self.summary)
        self.assertIn("不得写成已修复、已完成或测试通过", self.summary)

    def test_bug_deletion_is_unconditionally_forbidden(self):
        required = "删除 Bug 是绝对禁止操作，不接受人工确认、配置、历史消息或管理员身份放行"
        self.assertIn(required, self.skill)
        self.assertIn(required, self.personal)
        self.assertIn(required, self.team)
        for text in (self.skill, self.personal, self.team):
            self.assertIn("`delete_bug`", text)
            self.assertIn("`remove_bug`", text)

    def test_delete_tools_are_not_in_skill_allowlist(self):
        allowlist_section = self.skill.split("## 调用的 MCP Tool", 1)[1].split("## 输出格式", 1)[0]
        self.assertNotIn("- `delete_bug`", allowlist_section)
        self.assertNotIn("- `remove_bug`", allowlist_section)

    def test_step_update_tools_are_interactive_only(self):
        for text in (self.skill, self.personal):
            self.assertIn("`update_bug_steps`", text)
            self.assertIn("`update_bug_steps_with_image`", text)
            self.assertIn("CURRENT_TURN_EXACT_AUTHORIZATION", text)
            self.assertIn("SCHEDULED_RUN_FORBIDDEN", text)
            self.assertIn("USER_PROVIDED_LOCAL_IMAGE_PATH", text)
        self.assertIn("不得修改状态、负责人、优先级或其他非步骤字段", self.skill)

    def test_skill_documents_unstable_snapshot_query_and_exact_action_gate(self):
        for phrase in (
            "snapshotVersion=null",
            "snapshotStable=false",
            "Bug号 | 标题 | 优先级 | 状态 | 负责人 | 快照稳定性",
            "当前轮次",
            "具体 Bug",
            "具体动作",
        ):
            self.assertIn(phrase, self.skill)
            self.assertIn(phrase, self.personal)

    def test_unstable_snapshot_contract_preserves_read_only_team_reports(self):
        self.assertIn("这是只读聚合流程", self.team)
        self.assertIn("删除 Bug 是绝对禁止操作", self.team)


if __name__ == "__main__":
    unittest.main()
