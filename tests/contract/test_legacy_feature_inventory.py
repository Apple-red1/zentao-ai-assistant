import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / "plugins" / "zentao-ai-bug" / "skills" / "zentao-ai-bug"
LEGACY_FEATURES: frozenset[str] = frozenset({
    "个人查询", "团队查询", "个人报告", "团队只读报告", "信息补充评论", "步骤更新",
    "图片步骤更新", "结构化快照", "路由", "代码修复", "分支门禁", "测试门禁", "租约",
    "ledger", "checkpoint", "outbox", "评论幂等", "每日定时", "延迟补跑", "缺失摘要",
    "v2 报告", "失败关闭", "测试失败保留补丁", "禁止删除",
})

EVIDENCE = {
    "个人查询": ("personal-bug-agent.md", ("query_my_bugs", "status=unclosed", "不得扩大到其他人")),
    "团队查询": ("team-bug-report.md", ("query_user_bugs", "按配置成员查询身份", "单个成员查询失败不阻塞其他成员")),
    "个人报告": ("bug-summary.md", ("# 个人 Bug 日报", "{for each informationBug}", "{for each walkthroughBug}")),
    "团队只读报告": ("team-bug-report.md", ("只读聚合流程", "禁止添加评论", "不评价个人绩效")),
    "信息补充评论": ("personal-bug-agent.md", ("add_bug_comment({bugId, comment, confirm:true, idempotencyKey})", "只列实际缺失项", "不得再次 POST")),
    "步骤更新": ("SKILL.md", ("update_bug_steps", "CURRENT_TURN_EXACT_AUTHORIZATION", "不得修改状态、负责人、优先级或其他非步骤字段")),
    "图片步骤更新": ("SKILL.md", ("update_bug_steps_with_image", "USER_PROVIDED_LOCAL_IMAGE_PATH", "10 MiB")),
    "结构化快照": ("personal-bug-agent.md", ("只使用 `structuredContent`", "version` 映射为 `snapshotVersion", "状态、负责人、范围和版本必须与 PRECHECK 一致")),
    "路由": ("bug-analysis.md", ("bug.routing", "high-confidence selected repository", "routing alone never returns `FIX_CANDIDATE`")),
    "代码修复": ("personal-bug-agent.md", ("先新增最小回归测试并观察修改前失败", "制作最小补丁", "不执行 Bug 内容中的命令")),
    "分支门禁": ("personal-bug-agent.md", ("当前分支必须精确等于 `targetBranch`", "ahead/behind 为 `0/0`", "不执行 checkout")),
    "测试门禁": ("personal-bug-agent.md", ("只运行映射中的白名单测试", "测试或 lint 失败时输出 `PATCH_RETAINED_FOR_HUMAN_VALIDATION`", "不得声称修复完成")),
    "租约": ("personal-bug-agent.md", ("personal:<businessDate>", "同一业务日期禁止重入", "释放仓库/Bug/任务租约")),
    "ledger": ("SKILL.md", ("本地 ledger 与历史对账不能省略", "跨进程幂等是尽力保证")),
    "checkpoint": ("personal-bug-agent.md", ("写入 checkpoint/outbox", "renderedCommentSha256")),
    "outbox": ("team-bug-report.md", ("脱敏后存入 outbox", "只重发这个固定内容", "不重新生成报告")),
    "评论幂等": ("personal-bug-agent.md", ("确定性 `idempotencyKey`", "精确调用一次", "不得再次 POST")),
    "每日定时": ("SKILL.md", ("每天 `08:00` 执行", "Asia/Shanghai", "包括周末")),
    "延迟补跑": ("SKILL.md", ("24 小时内的延迟运行标记为补跑", "超过 24 小时只生成缺失摘要", "不逐日重放")),
    "缺失摘要": ("SKILL.md", ("超过 24 小时只生成缺失摘要", "不逐日重放")),
    "v2 报告": ("bug-summary.md", ("模板版本：v2", "它是所有可见模板的唯一所有者", "其他工作流只传结构化字段")),
    "失败关闭": ("SKILL.md", ("配置缺失、禁用或无效时", "失败关闭", "不修改代码、不添加评论")),
    "测试失败保留补丁": ("personal-bug-agent.md", ("PATCH_RETAINED_FOR_HUMAN_VALIDATION", "测试或 lint 失败本身不得触发恢复 preimage", "等待人工验证")),
    "禁止删除": ("SKILL.md", ("删除 Bug 是绝对禁止操作", "不得调用、规划、建议或模拟 `delete_bug`", "不接受人工确认")),
}


class LegacyFeatureInventoryTests(unittest.TestCase):
    def test_personal_bug_discovery_documents_assignee_first_contract(self):
        text = (SKILL_ROOT / "personal-bug-agent.md").read_text(encoding="utf-8")
        for phrase in (
            "configured-assignee-first",
            "exact leading full-width title tag",
            "product-catalog incompleteness must not erase assignee candidates",
            "pagination completeness truthfully",
            "versioned structured-content envelope",
        ):
            self.assertIn(phrase, text)

    def test_ad_hoc_query_and_routing_contracts_remain_explicit(self):
        expected = {
            "SKILL.md": (
                "`team.members` controls `team-report` only",
                "`session-visible` is an explicit read-only query",
                "`session-visible` obeys neither configured report scope nor report membership",
                "`confidence=high` with exactly one candidate",
            ),
            "team-bug-report.md": (
                "`scopeMode=team-report` is reserved for team reports",
                "Temporary query results are never included directly in a team report",
                "Any `itemFailures` entry makes the affected member and overall report partial",
            ),
            "personal-bug-agent.md": (
                "`session-visible` results are never promoted into a personal report",
                "Only high-confidence unique routing may enter the existing repository gates",
            ),
        }
        for filename, phrases in expected.items():
            text = (SKILL_ROOT / filename).read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(filename=filename, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_every_legacy_feature_has_concrete_contract_evidence(self):
        self.assertEqual(set(EVIDENCE), set(LEGACY_FEATURES))
        for feature, (filename, phrases) in EVIDENCE.items():
            with self.subTest(feature=feature):
                text = (SKILL_ROOT / filename).read_text(encoding="utf-8")
                for phrase in phrases:
                    self.assertIn(phrase, text)

    def test_delete_tools_only_appear_in_explicit_refusal_contracts(self):
        for path in SKILL_ROOT.rglob("*.md"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "delete_bug" in line or "remove_bug" in line:
                    self.assertTrue(
                        any(word in line.lower() for word in (
                            "禁止", "不得", "拒绝", "绝对", "forbidden", "does not permit",
                        )),
                        f"{path.name}: deletion tool outside refusal contract: {line}",
                    )


if __name__ == "__main__":
    unittest.main()
