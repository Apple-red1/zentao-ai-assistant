from __future__ import annotations

import re
import shlex
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

    def test_templates_have_three_distinct_fixed_prefixes(self) -> None:
        self.assertEqual(1, TEMPLATES.count("[CODEX-HUMAN-ATTESTED-RESOLUTION]"))
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

    def human_workflow(self) -> str:
        self.assertIn("## 0. HUMAN_ATTESTED_RESOLVE", WORKFLOW)
        return section(WORKFLOW, "## 0. HUMAN_ATTESTED_RESOLVE", "## 1. 执行面")

    def test_human_routing_distinguishes_completion_from_requests_and_uncertainty(self) -> None:
        human = self.human_workflow()
        for example, outcome in (
            ("3641 已解决", "HUMAN_ATTESTED_RESOLVE"),
            ("Bug #3641 解决了，更新禅道", "HUMAN_ATTESTED_RESOLVE"),
            ("把刚才那个 Bug 标记已解决", "上下文唯一"),
            ("刚才那个已解决", "多个目标时提问"),
            ("#3641、#3642 已解决", "输入顺序串行"),
            ("处理一下", "普通流程"),
            ("看一下", "普通流程"),
            ("修一下", "普通流程"),
            ("帮我解决 Bug #3641", "普通流程"),
            ("修复后标记已解决", "普通流程"),
            ("应该好了", "不触发"),
            ("可能没问题了", "不触发"),
        ):
            with self.subTest(example=example):
                row = next((line for line in human.splitlines() if line.startswith(f"| {example} |")), "")
                self.assertIn(outcome, row)
        self.assertIn("当前消息", human)
        self.assertIn("RESOLVE_R2_ALLOWED", human)
        self.assertIn("不是 SOLVABLE", human)
        self.assertIn("普通证据流程", SKILL)
        self.assertNotIn("指代不唯一或没有 ID 时先提问", SKILL)

    def test_human_path_skips_business_audit_and_only_uses_basic_cli(self) -> None:
        human = self.human_workflow()
        skip = section(human, "### 0.2", "### 0.3")
        for operation in ("AGENTS.md", "git status", "git diff", "snapshot", "compare", "附件", "源码", "commit", "push", "merge", "SHA", "test", "lint", "typecheck", "build", "patch"):
            self.assertIn(operation, skip)
        self.assertIn("不执行也不要求", skip)
        commands = re.findall(r"```bash\n(.*?)\n```", human, re.S)
        self.assertEqual(3, len(commands))
        parsed = [shlex.split(command.replace("\\\n", "")) for command in commands]
        self.assertEqual(["view", "resolve", "view"], [argv[3] for argv in parsed])
        self.assertTrue(all(argv[:3] == ["python", "skills/zentao/scripts/zentao.py", "bug"] for argv in parsed))
        resolve = parsed[1]
        self.assertEqual(1, resolve.count("--resolved-build"))
        self.assertEqual("trunk", resolve[resolve.index("--resolved-build") + 1])
        self.assertEqual("fixed", resolve[resolve.index("--resolution") + 1])
        self.assertNotIn("--assignee", resolve)
        self.assertNotIn("--resolved-date", resolve)
        self.assertIn("--comment-file", resolve)
        self.assertIn("覆盖", human)

    def test_human_state_queue_and_failure_contract(self) -> None:
        human = self.human_workflow()
        for anchor in (
            "active", "resolved", "closed", "不重复写", "每个 active Bug 最多一次 resolve",
            "严格串行", "当前消息明确列出", "不读取后续 Bug", "UNKNOWN_WRITE_RESULT",
            "停止整个队列", "绝不重试原 resolve", "只读回读", "无法确认", "unknown",
            "trunk", "真实错误", "不猜版本", "不自动重试", "不自动 close",
            "edit/close/activate", "不是 CAS", "stderr", "status=success",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, human)
        self.assertNotIn("默认不传 `--resolved-build`", human)

    def test_human_comment_template_has_no_synthetic_evidence(self) -> None:
        self.assertIn("## Human-attested", TEMPLATES)
        human = section(TEMPLATES, "## Human-attested", "## Fixed")
        blocks = re.findall(r"```text\n(.*?)\n```", human, re.S)
        self.assertEqual(1, len(blocks))
        template = blocks[0]
        self.assertTrue(template.startswith("[CODEX-HUMAN-ATTESTED-RESOLUTION]\n\n"))
        self.assertIn("用户已明确确认 Bug #<id> 已解决。", template)
        self.assertIn("resolution=fixed", template)
        self.assertIn("trunk", template)
        for fabricated in ("测试通过", "commit", "push", "merge", "SHA", "symbol", "diff", "<path>", "<command>"):
            self.assertNotIn(fabricated, template)
        for anchor in ("UTF-8", "用户提供", "原意", "覆盖", "不编造"):
            self.assertIn(anchor, human)

    def test_ui_prompt_routes_before_business_evidence(self) -> None:
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$zentao-bug-resolver", metadata)
        self.assertIn("HUMAN_ATTESTED_RESOLVE", metadata)
        self.assertNotIn("先读取当前 Bug snapshot", metadata)


if __name__ == "__main__":
    unittest.main()
