# 禅道 Bug 步骤图片更新能力实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为本机自写禅道 MCP 增加受控的步骤编辑和图片上传工具，并同步本机 Skill 权限契约。

**Architecture:** `ZentaoApi` 负责 Web 编辑表单、multipart 提交和更新后读取；Bug 工具层负责输入验证、确认门槛及结构化结果；Skill 负责限定交互授权并禁止定时任务调用。

**Tech Stack:** Node.js 24、MCP SDK、Zod、Node test runner、Markdown Skill、Python unittest。

## Global Constraints

- 图片仅允许 PNG/JPEG/WebP 普通文件，最大 10 MiB。
- 所有写入要求 `confirm:true`，定时日报禁止调用。
- 不修改 Bug 状态、负责人、优先级或其他非目标字段。
- 删除 Bug 永久禁止。
- 不在自动测试中访问真实禅道。

---

### Task 1: API 表单与图片上传

**Files:**
- Modify: `C:/Users/wwtlove66/Documents/Codex/2026-07-10/https-xm-wixcn-com-index-php/zentao-mcp-server/src/services/zentao-api.js`
- Test: `C:/Users/wwtlove66/Documents/Codex/2026-07-10/https-xm-wixcn-com-index-php/zentao-mcp-server/tests/zentao-api.test.js`

**Interfaces:**
- Produces: `updateBugSteps(bugId, { steps })` and `updateBugStepsWithImage(bugId, { steps, imagePath, imageAlt })`.

- [ ] Add failing tests for preserving required Bug fields, reading the Web edit form, multipart image upload, extension/size checks, and post-update detail query.
- [ ] Run `npm test`; expect the new tests to fail.
- [ ] Implement minimal file validation, hidden-input extraction, multipart submission and structured result.
- [ ] Run `npm test`; expect pass.

### Task 2: MCP 工具注册

**Files:**
- Modify: `C:/Users/wwtlove66/Documents/Codex/2026-07-10/https-xm-wixcn-com-index-php/zentao-mcp-server/src/tools/bug.js`
- Modify: `C:/Users/wwtlove66/Documents/Codex/2026-07-10/https-xm-wixcn-com-index-php/zentao-mcp-server/tests/server.test.js`

**Interfaces:**
- Produces: `update_bug_steps` and `update_bug_steps_with_image`, both requiring `confirm:true`.

- [ ] Add failing registration/schema/handler tests.
- [ ] Run `npm test`; expect failure.
- [ ] Register both tools through `registerBugTool`, validate arguments, and return structured before/after/attachment data.
- [ ] Run `npm test`; expect pass and deletion-guard tests remain green.

### Task 3: Skill 权限契约

**Files:**
- Modify: `C:/Users/wwtlove66/.codex/skills/zentao-ai-bug/SKILL.md`
- Modify: `C:/Users/wwtlove66/.codex/skills/zentao-ai-bug/personal-bug-agent.md`
- Modify: `F:/每日工作/tests/test_zentao_skill_contract.py`

**Interfaces:**
- Produces: current-turn exact authorization contract; scheduled runs always refuse the two tools.

- [ ] Add failing static tests for exact authorization, current-user path origin, scheduled-run refusal, and unchanged delete prohibition.
- [ ] Run Skill tests; expect failure.
- [ ] Update Skill tool and permission sections.
- [ ] Run all workspace tests; expect pass.

### Task 4: Final verification

**Files:**
- Verify all modified files.

- [ ] Run MCP `npm test` and `node --check` for changed JavaScript.
- [ ] Run all workspace Python tests.
- [ ] Search for delete-tool regressions and unguarded registrations.
- [ ] Report changed files and restart requirement without committing or publishing.
