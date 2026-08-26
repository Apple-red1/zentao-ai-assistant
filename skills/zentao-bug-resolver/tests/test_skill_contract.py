from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
WORKFLOW = (SKILL_DIR / "references" / "workflow.md").read_text(encoding="utf-8")
TEMPLATES = (SKILL_DIR / "references" / "comment-templates.md").read_text(encoding="utf-8")


def section(text: str, start: str, end: str | None = None) -> str:
    start_at = text.index(start)
    body = text[start_at:]
    if end is not None:
        body = body[: body.index(end)]
    return body


class BugResolverSkillContractTests(unittest.TestCase):
    """Static contract checks for the T04 workflow and lifecycle templates."""

    def test_workflow_declares_the_three_authorization_levels(self) -> None:
        for level in ("ANALYZE_ONLY", "LOCAL_FIX_ALLOWED", "RESOLVE_R2_ALLOWED"):
            with self.subTest(level=level):
                self.assertIn(level, WORKFLOW)
        self.assertIn("授权针对当前请求和当前 Bug，不从历史对话、其它 Bug 或 pending queue 继承", WORKFLOW)

    def test_workflow_declares_the_four_evidence_categories(self) -> None:
        categories = ("SOLVABLE", "UNCLEAR", "NO_CODE_EVIDENCE", "BLOCKED")
        for category in categories:
            with self.subTest(category=category):
                self.assertIn(f"### `{category}`", WORKFLOW)

    def test_vague_request_is_at_most_local_fix(self) -> None:
        self.assertIn("| 模糊“处理这个 Bug” | `LOCAL_FIX_ALLOWED` | 不能推断 R2 |", WORKFLOW)
        self.assertIn("不能推断 R2", WORKFLOW)
        self.assertIn("不等于 resolve 授权", SKILL)

    def test_pending_queue_requires_explicit_continuation_and_does_not_inherit_authority(self) -> None:
        for anchor in (
            "pending_queue",
            "pending_queue` 不会自动继续",
            "当前 Bug 得出最终结论后停止本次任务",
            "用户必须再次明确继续",
            "重新解析该 Bug 的授权与起始 snapshot",
            "当前 Bug 的授权不继承",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, WORKFLOW + SKILL)

    def test_fixed_r2_gate_and_command_anchor(self) -> None:
        fixed = section(WORKFLOW, "### 5.5 fixed R2 分支", "### 5.6 unclear/no-code 信息退回分支")
        for anchor in (
            "RESOLVE_R2_ALLOWED",
            "SOLVABLE",
            "直接代码证据和最小修改已完成",
            "实际验证通过",
            "diff 已审阅",
            "compare 未变化",
            "resolved-build",
            "明确、可用的测试账号",
            "--resolution fixed",
            "--resolved-build",
            "--assignee",
            "--comment-file",
            "显式 snapshot 或 `bug view` 回读",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, fixed)

    def test_unclear_no_code_r2_gate_and_command_anchor(self) -> None:
        unclear = section(WORKFLOW, "### 5.6 unclear/no-code 信息退回分支", "## 6. 错误与安全")
        for anchor in (
            "RESOLVE_R2_ALLOWED",
            "当前状态实际为 active",
            "creator_account",
            "写前 compare unchanged",
            "[CODEX-BUG-UNCLEAR]",
            "本次未修改业务代码",
            "证据不足",
            "补充清单",
            "will-not-fix",
            "信息不足退回流程",
            "显式 `activate`",
            "--resolution will-not-fix",
            "--assignee <snapshot.creator_account>",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, unclear)

    def test_lifecycle_automation_and_standalone_paths_are_forbidden(self) -> None:
        self.assertIn("不得自动 close、activate、delete、连续处理下一 Bug", SKILL)
        self.assertIn("不得用生命周期动作伪造 standalone comment", SKILL)
        self.assertIn("不以 edit/activate/close 仅留下分析 comment 或单独转派 active Bug", WORKFLOW)
        self.assertIn("写结果未知", WORKFLOW)
        self.assertIn("UNKNOWN_WRITE_RESULT", WORKFLOW)
        self.assertIn("绝不重试原 resolve", WORKFLOW)

    def test_templates_have_exactly_two_fixed_prefixes(self) -> None:
        self.assertEqual(1, TEMPLATES.count("[CODEX-BUG-RESOLUTION]"))
        self.assertEqual(1, TEMPLATES.count("[CODEX-BUG-UNCLEAR]"))
        fixed_start = TEMPLATES.index("[CODEX-BUG-RESOLUTION]")
        unclear_start = TEMPLATES.index("[CODEX-BUG-UNCLEAR]")
        self.assertGreaterEqual(fixed_start, 2)
        self.assertEqual("\n\n", TEMPLATES[fixed_start - 2:fixed_start])
        self.assertGreaterEqual(unclear_start, 2)
        self.assertEqual("\n\n", TEMPLATES[unclear_start - 2:unclear_start])
        self.assertEqual(
            "[CODEX-BUG-RESOLUTION]\n\n## 结论 / Conclusion",
            TEMPLATES[fixed_start:fixed_start + len("[CODEX-BUG-RESOLUTION]\n\n## 结论 / Conclusion")],
        )
        self.assertEqual(
            "[CODEX-BUG-UNCLEAR]\n\n## 结论 / Conclusion",
            TEMPLATES[unclear_start:unclear_start + len("[CODEX-BUG-UNCLEAR]\n\n## 结论 / Conclusion")],
        )

    def test_fixed_template_contains_required_evidence_change_verification_compare_readback_sections(self) -> None:
        fixed = section(TEMPLATES, "[CODEX-BUG-RESOLUTION]", "[CODEX-BUG-UNCLEAR]")
        for heading in (
            "## 结论 / Conclusion",
            "## 证据 / Evidence",
            "## 修改 / Change",
            "## 验证 / Verification",
            "## 写前 compare / Pre-write compare",
            "## Lifecycle resolve",
            "## 显式回读 / Readback",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, fixed)
        for anchor in (
            "实际行为（actual behavior）",
            "期望行为（expected behavior）",
            "根因",
            "代码证据",
            "最小修改边界",
            "验证命令",
            "实际结果",
            "changed=false",
            "--resolution fixed",
            "显式回读",
            "snapshot",
            "状态",
            "本次最多一次明确的 `bug resolve`",
            "不重试未知写结果",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, fixed)
        self.assertRegex(fixed, r"写入次数：本次最多一次明确的 `bug resolve`；不重试未知写结果。")
        resolve_commands = re.findall(
            r"python skills/zentao/scripts/zentao\.py bug resolve <bug-id>.*?(?=\n\n|\Z)", fixed, re.S
        )
        self.assertEqual(1, len(resolve_commands))
        self.assertEqual(1, resolve_commands[0].count("bug resolve"))
        self.assertNotIn("bug close", resolve_commands[0])
        self.assertNotIn("bug activate", resolve_commands[0])

    def test_unclear_template_contains_required_information_return_sections(self) -> None:
        unclear = section(TEMPLATES, "[CODEX-BUG-UNCLEAR]")
        for heading in (
            "## 结论 / Conclusion",
            "## 证据状态 / Evidence status",
            "## 本次代码修改 / Code change",
            "## 证据不足 / Missing evidence",
            "## 补充清单 / Requested additions",
            "## R2 门槛与 will-not-fix 信息退回",
            "## 显式回读与后续 / Readback and next step",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, unclear)
        for anchor in (
            "本次未修改业务代码",
            "证据不足",
            "补充清单",
            "will-not-fix",
            "仅表示信息不足的退回流程",
            "不表示已修复",
            "不表示没有问题",
            "RESOLVE_R2_ALLOWED",
            "当前状态实际为 `active`",
            "creator_account",
            "changed=false",
            "--resolution will-not-fix",
            "显式 `activate`",
            "assignee：`<snapshot.creator_account>`",
            "当前用户明确给出当前 Bug 的 `RESOLVE_R2_ALLOWED`；当前状态实际为 `active`；起始/当前 snapshot 有非空且明确 account 形式的 `creator_account`；写前 `compare` 结果为 `changed=false`",
            "仅是信息不足退回流程，不是已修复或无问题结论",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, unclear)
        gate = re.search(r"只有同时满足以下条件.*?任一条件缺失时不写入，只报告 missing facts。", unclear, re.S)
        self.assertIsNotNone(gate)
        gate_text = gate.group(0)
        self.assertRegex(gate_text, r"RESOLVE_R2_ALLOWED.*active.*creator_account.*changed=false")
        self.assertNotIn("或", gate_text)
        self.assertRegex(unclear, r"assignee：`<snapshot\.creator_account>`[\s\S]*--assignee <snapshot\.creator_account>")
        unclear_commands = re.findall(
            r"python skills/zentao/scripts/zentao\.py bug resolve <bug-id>.*?(?=\n\n|\Z)", unclear, re.S
        )
        self.assertEqual(1, len(unclear_commands))
        self.assertIn("--resolution will-not-fix", unclear_commands[0])
        self.assertIn("--assignee <snapshot.creator_account>", unclear_commands[0])
        self.assertIn("仅是信息不足退回流程，不是已修复或无问题结论", unclear)
        self.assertNotIn("resolution：`fixed`", unclear)

    def test_skill_links_the_template_document(self) -> None:
        self.assertIn("references/comment-templates.md", SKILL)


if __name__ == "__main__":
    unittest.main()
