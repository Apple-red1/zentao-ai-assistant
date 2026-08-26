---
name: zentao-bug-resolver
description: Use when a user asks to investigate, fix, or explicitly resolve a ZenTao Bug through an evidence-first workflow that combines current ZenTao facts with the business repository.
---

# 禅道 Bug 证据驱动修复（zentao-bug-resolver）

本 Skill 一次只处理 `select` 产生的 `current_bug_id`。先读取当前 Bug、必要的附件和业务代码证据，再按证据分类；不能用猜测替代复现、实际/期望行为或源码根因。

## 只读入口

```bash
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py select --bug-id 123 --json
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py snapshot --bug-id 123 --json
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py compare --bug-id 123 --baseline-file <snapshot.json> --json
```

选择器支持 Bug ID、人员、产品/项目/执行、数值 module ID、状态/优先级/严重程度及可识别的创建/更新时间条件；结果会保留完整性、分页失败、缺字段和 `pending_queue`。`pending_queue` 不会自动继续。

## 授权边界

- `ANALYZE_ONLY`：只读取 ZenTao 与业务仓库并给出证据分类。
- `LOCAL_FIX_ALLOWED`：允许在证据充分时修改和验证业务代码，但不写 ZenTao。
- `RESOLVE_R2_ALLOWED`：只有当前用户明确要求生命周期 resolve，并且 workflow 的全部证据、验证、diff、并发复查和账号门槛通过时，才允许调用基础 `zentao` CLI 一次并回读。

“处理 Bug”最多推断为 `LOCAL_FIX_ALLOWED`，不等于 resolve 授权。`UNCLEAR`、`NO_CODE_EVIDENCE` 不得修改代码；`BLOCKED` 不得绕过门槛写入。

## 固定流程与禁区

`select → current Bug snapshot → 详情/资源证据 → 业务仓库约束与 git status → 源码证据/分类 → 最小修改与真实验证 → 写前 compare → 明确 R2 下一次 bug resolve → 显式回读`。

详细状态机、证据门、`will-not-fix` 信息退回分支、并发和错误规则见 [`references/workflow.md`](references/workflow.md)。生命周期 comment 模板见 [`references/comment-templates.md`](references/comment-templates.md)。

resolver Python 脚本只做 ZenTao 读取和确定性处理；生命周期写入属于 Agent 编排，必须回到基础 `zentao` CLI。不得自动 close、activate、delete、连续处理下一 Bug、提交/推送/合并/部署，也不得用生命周期动作伪造 standalone comment 或 active Bug 单独转派。
