# 禅道补丁保留与删除禁令实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 更新本机禅道 Skill 与自写 MCP，使测试失败的安全补丁保留给人工验证，并从服务端和技能层永久禁止删除 Bug。

**Architecture:** Skill 层负责行为决策、报告真实性和权限矩阵；MCP 层通过统一工具注册守卫拒绝删除类工具。两层分别使用静态契约测试和 Node 单元测试防止回归。

**Tech Stack:** Markdown Skill、Node.js MCP Server、Node test runner、Python unittest/静态契约测试。

## Global Constraints

- 测试或 lint 失败不得返回 `FIX_CANDIDATE`，不得声称修复完成或发送成功评论。
- HEAD、分支、暂存区和 AI postimage 可验证时保留未提交补丁，等待人工验证。
- 删除 Bug 永久禁止，任何确认、配置或管理员身份均不能放行。
- 不 commit、push、merge 或 deploy。

---

### Task 1: Skill 补丁保留契约

**Files:**
- Modify: `C:/Users/wwtlove66/.codex/skills/zentao-ai-bug/personal-bug-agent.md`
- Modify: `C:/Users/wwtlove66/.codex/skills/zentao-ai-bug/bug-analysis.md`
- Modify: `C:/Users/wwtlove66/.codex/skills/zentao-ai-bug/bug-summary.md`
- Test: `F:/每日工作/tests/test_zentao_skill_contract.py`

**Interfaces:**
- Consumes: `BugAnalysisResult.decision`, HEAD/branch/staging/postimage evidence.
- Produces: `PATCH_RETAINED_FOR_HUMAN_VALIDATION` report semantics without `FIX_CANDIDATE`.

- [ ] Add failing static tests asserting that test/lint failures retain verified postimages and never imply completion.
- [ ] Run `python -m unittest tests.test_zentao_skill_contract -v`; expect failure against the old preimage-restore rule.
- [ ] Replace automatic restoration on test failure with verified postimage retention and explicit human-validation reporting.
- [ ] Update analysis and rendering contracts so failed gates remain `TOOL_OR_PERMISSION_GAP` or `NEEDS_ENGINEER_REVIEW`.
- [ ] Re-run the static contract tests; expect pass.

### Task 2: Skill 删除 Bug 绝对禁令

**Files:**
- Modify: `C:/Users/wwtlove66/.codex/skills/zentao-ai-bug/SKILL.md`
- Modify: `C:/Users/wwtlove66/.codex/skills/zentao-ai-bug/personal-bug-agent.md`
- Modify: `C:/Users/wwtlove66/.codex/skills/zentao-ai-bug/team-bug-report.md`
- Test: `F:/每日工作/tests/test_zentao_skill_contract.py`

**Interfaces:**
- Produces: unconditional refusal for `delete_bug`, `remove_bug`, and equivalent permanent deletion.

- [ ] Add failing tests requiring an absolute delete prohibition and forbidding confirmation-based exceptions.
- [ ] Run the static contract tests; expect failure.
- [ ] Add the absolute prohibition to top-level and personal/team permission sections.
- [ ] Re-run the static contract tests; expect pass.

### Task 3: MCP 工具注册守卫

**Files:**
- Modify: `C:/Users/wwtlove66/Documents/Codex/2026-07-10/https-xm-wixcn-com-index-php/zentao-mcp-server/src/tools/bug.js`
- Modify: `C:/Users/wwtlove66/Documents/Codex/2026-07-10/https-xm-wixcn-com-index-php/zentao-mcp-server/tests/server.test.js`

**Interfaces:**
- Produces: `registerBugTool(server, name, config, handler)` which throws for normalized deletion names before registration.

- [ ] Add failing Node tests asserting `delete_bug` and `remove_bug` cannot register and the normal tool set contains neither name.
- [ ] Run `npm test`; expect the new guard test to fail.
- [ ] Implement a minimal forbidden-name set and route Bug tool registrations through the guard.
- [ ] Run `npm test`; expect pass.

### Task 4: Integrated verification

**Files:**
- Verify all files above.

- [ ] Run the Skill static contract tests.
- [ ] Run MCP `npm test`.
- [ ] Search both trees for contradictory automatic-restore wording and delete-tool allowances.
- [ ] Report exact pass/fail results and changed files; do not commit or publish.
