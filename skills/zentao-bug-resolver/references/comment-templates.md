# ZenTao Bug lifecycle comment templates

这些模板只用于 Agent 已经满足 `workflow.md` 对当前 Bug 的写入门槛之后。模板本身不授予生命周期写入权限；缺少任一门槛时，只报告缺失事实，不调用 lifecycle endpoint。

## Human-attested：人工确认已解决

只用于 `HUMAN_ATTESTED_RESOLVE`。当前用户明确确认当前 Bug 已解决即提供该分支 R2 授权；不套用下方普通 Fixed 模板的代码、测试、账号或 compare 门槛。

用户未提供解决说明时，自动生成以下最小 UTF-8 备注（替换实际 ID）：

```text
[CODEX-HUMAN-ATTESTED-RESOLUTION]

用户已明确确认 Bug #<id> 已解决。
本次按人工确认执行 resolution=fixed。
本次解决版本参数默认使用主干（trunk）。
```

用户提供解决说明时，在末尾追加“用户说明：”并按原意整理，不将用户描述改写成 Agent 验证事实。用户明确指定其它解决版本时，用“本次解决版本参数按用户指定使用 <explicit-build>。”覆盖主干那一行，与实际命令一致。这里记录的是调用参数，不是代码已在某版本修复的独立证据。

不编造测试通过、commit/push/merge/SHA、修改文件/symbol、diff 或自动审计结论；不追问这些事实。每个 Bug 单独生成文件，不能把上一 Bug 的说明带入下一 Bug。具体 CLI 和错误规则以 workflow 第 0 节为准。

## Fixed：`SOLVABLE` 修复回写

仅当当前用户针对当前 Bug 明确给出 `RESOLVE_R2_ALLOWED`，证据分类为 `SOLVABLE`，业务代码最小修改已经完成且真实验证通过，写前 `compare` 为 unchanged，并且 resolved-build 与 assignee 都有明确事实依据时使用。把占位符替换为实际观察，不要把计划或猜测写成结果。

[CODEX-BUG-RESOLUTION]

## 结论 / Conclusion

- Bug：`<bug-id>` / `<title>`
- 证据分类：`SOLVABLE`
- 当前授权：`RESOLVE_R2_ALLOWED`（当前用户、当前 Bug 的明确授权）
- ZenTao resolution：`fixed`
- 一句话结论：<说明实际根因和已完成的最小修复>

## 证据 / Evidence

- 复现条件或失败触发条件：<环境、输入、步骤、边界>
- 实际行为（actual behavior）：<可观察结果>
- 期望行为（expected behavior）：<Bug/产品契约支持的结果>
- 根因：<从证据推导出的具体原因；不填业务常识猜测>
- 代码证据：`<path>:<symbol>`，调用路径：`<caller -> ... -> root cause>`
- 证据完整性限制：<若有 partial/unavailable，明确列出；无则填“无”>

## 修改 / Change

- 修改文件与 symbol：`<path>:<symbol>`
- 修改内容：<实际改动及其如何消除根因>
- 最小修改边界：<为什么没有扩大范围>
- diff 审阅：<已检查的 diff 范围；不得包含当前 Bug 无关改动或秘密>

## 验证 / Verification

- 验证命令（完整原文）：`<command>`
- 实际结果：<通过/失败、关键断言或输出>
- 退出码：`<code>`
- 验证结论：<只有真实通过后才能填写“通过”；未通过不得使用 fixed 模板>

## 写前 compare / Pre-write compare

- 起始 snapshot：`<baseline-file>`
- 命令：`python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py compare --bug-id <bug-id> --baseline-file <baseline-file> --json`
- 结果：`changed=false`
- 复查结论：关键字段未变化；若 `changed=true`、比较失败或关键事实不可安全比较，停止写入，不覆盖并发变化。

## Lifecycle resolve

- 写入次数：本次最多一次明确的 `bug resolve`；不重试未知写结果。
- resolved-build：`<fact-supported-build-or-trunk>`（只能填写有事实依据的值）
- assignee：`<explicit-test-account>`（只能填写明确可用的测试账号）
- 命令：

  ```bash
  python skills/zentao/scripts/zentao.py bug resolve <bug-id> \
    --resolution fixed \
    --resolved-build <fact-supported-build-or-trunk> \
    --assignee <explicit-test-account> \
    --comment-file <utf8-file> \
    --json
  ```

## 显式回读 / Readback

- 回读命令：`python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py snapshot --bug-id <bug-id> --json`（或明确的 `bug view`）
- 回读结果：<实际状态、resolution、assignee、comment 结果>
- 回读结论：<仅根据回读事实确认写入；若写结果未知或状态无法证明，保留 unknown/blocked>
- 后续边界：本模板不自动 `close`、`activate`、`delete`，不自动处理下一 Bug，也不把生命周期动作当作 standalone comment。

## Unclear / no-code evidence：信息不足退回

用于 `UNCLEAR` 或 `NO_CODE_EVIDENCE`。这不是技术修复结论；没有满足 R2 全部门槛时不得写入。即使满足退回门槛，也只用一次 `will-not-fix` 信息退回，不得表述为已修复或无问题。

[CODEX-BUG-UNCLEAR]

## 结论 / Conclusion

- Bug：`<bug-id>` / `<title>`
- 证据分类：`UNCLEAR` 或 `NO_CODE_EVIDENCE`
- 当前授权：`RESOLVE_R2_ALLOWED`（若没有当前用户对当前 Bug 的明确授权，停止写入）
- 本次未修改业务代码。
- `will-not-fix` 语义：仅表示信息不足的退回流程，不表示已修复，也不表示没有问题。

## 证据状态 / Evidence status

- 已确认事实：<当前 Bug、资源、业务仓库和代码检查中实际观察到的事实>
- 当前状态：`<active/other>`；<若不是 active，说明不能走信息退回>
- 代码证据结论：<为何没有直接根因/负责 symbol，或为何复现、actual、expected 等事实仍不足>
- 完整性限制：<complete、partial_failures、unavailable_fields 等实际结果>

## 本次代码修改 / Code change

- 本次未修改业务代码。
- 原因：<证据不足或没有可证明的代码修改点>
- 不采取的猜测性改动：<列出避免的修改>

## 证据不足 / Missing evidence

- 缺失事实：<复现条件 / actual / expected / 源码根因 / 资源 / 权限等>
- 阻止原因：<说明为什么现有证据不能安全地修改代码或声称 fixed>

## 补充清单 / Requested additions

- [ ] <请补充可复现步骤、输入、环境或日志>
- [ ] <请补充实际行为与期望行为的可核对样例>
- [ ] <请补充产品/验收契约、相关资源或负责代码位置>
- [ ] <其它必要事实：<item>>

## R2 门槛与 will-not-fix 信息退回

只有同时满足以下条件才可使用本模板执行一次 `will-not-fix`：当前用户明确给出当前 Bug 的 `RESOLVE_R2_ALLOWED`；当前状态实际为 `active`；起始/当前 snapshot 有非空且明确 account 形式的 `creator_account`；写前 `compare` 结果为 `changed=false`。任一条件缺失时不写入，只报告 missing facts。

- 写入语义：这里的 `will-not-fix` 仅是信息不足退回流程，不是已修复或无问题结论。
- assignee：`<snapshot.creator_account>`，不得用只有姓名的猜测账号。
- 命令：

  ```bash
  python skills/zentao/scripts/zentao.py bug resolve <bug-id> \
    --resolution will-not-fix \
    --assignee <snapshot.creator_account> \
    --comment-file <utf8-file> \
    --json
  ```

## 显式回读与后续 / Readback and next step

- 回读命令：`python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py snapshot --bug-id <bug-id> --json`（或明确的 `bug view`）
- 回读结果：<实际状态、resolution、assignee、comment 结果；未知写结果保持 unknown/blocked>
- 后续：补齐信息后，需要用户再次明确授权并显式 `activate`，再重新开始该 Bug 的处理；本次不会自动 `activate`，不会自动继续下一 Bug，也不会用其它 lifecycle 动作代替。
