---
name: zentao-bug-resolver
description: Investigate or fix ZenTao Bugs using business code evidence, or mark Bugs resolved when the user explicitly confirms they are already solved (已解决 / 解决了 / 标记已解决). A request to fix a Bug is not confirmation that it is solved.
---

# 禅道 Bug 修复与人工确认解决（zentao-bug-resolver）

先按**当前消息**选择路径，再读取对应证据。执行前读取 [`references/workflow.md`](references/workflow.md) 的对应分支；生命周期备注使用 [`references/comment-templates.md`](references/comment-templates.md) 中对应模板。

## Bug 链接请求优先路由

当用户只要求 Bug URL、链接或详情链接时，直接执行 `python skills/zentao/scripts/zentao.py bug web-url <id> [<id> ...] --json`。链接格式固定为 `ZENTAO_BASE_URL/index.php?m=bug&f=view&bugID=<id>`；禁止打开浏览器、检查登录页、访问详情页或猜测其它格式。只有用户要求调查、修复或 resolve 时，才进入下面的证据流程。

## 人工确认：`HUMAN_ATTESTED_RESOLVE`

用户明确确认“已解决 / 解决了 / 标记已解决”，且 Bug ID 明确或当前上下文只有一个正在处理的 Bug，即视为该 Bug 的人工业务结论和 `RESOLVE_R2_ALLOWED`。例如“3641 已解决”“Bug #3641 解决了，更新禅道”。没有明确 ID 且无法从当前上下文唯一确定目标时才提问，不猜目标。

“帮我解决 / 修复 Bug”“修复后标记已解决”仍是普通证据流程；“应该好了 / 可能没问题了”、否定、条件、引用内容不构成人工确认。不得仅按关键词触发写入。

本分支直接执行：**最小 bug view → active 时一次 fixed resolve → 显式 bug view 回读**。不运行 select/snapshot/compare，不读取业务仓库、附件、源码、提交、测试、diff 或 patch，不重新审计用户的结论，也不要求补充这些事实。

- 默认显式使用 `--resolved-build trunk`；用户明确指定其它解决版本时覆盖此值。
- 自动生成 UTF-8 的 HUMAN-ATTESTED 备注；不编造代码、测试或提交事实。
- 默认不传 `--assignee`、`--resolved-date`，不提前追问负责人、备注、版本、日期或提交信息。
- 已 `resolved` / `closed` 不重复写；其它状态、字段校验、权限或不可确认的结果按 workflow 的真实阻塞处理。
- 当前消息明确列出多个已解决 Bug 时，按输入顺序去重并严格串行处理；只处理这些 ID。任一真实阻塞停止，不读取后续 Bug。`UNKNOWN_WRITE_RESULT` 停止整个队列，绝不重试原 resolve，只读回读。
- 结果以实际回读为准；不自动 close、activate、delete，不通过 edit/close/activate 绕过失败。

本分支只改变 Agent 编排，不增加 resolver script 或 facade 写能力。

## 普通证据流程：分析 / 修复

以下门槛只用于普通证据流程，不追加到人工确认分支。本流程一次只处理 `select` 产生的 `current_bug_id`。先读取当前 Bug、必要的附件和业务代码证据，再按证据分类；不能用猜测替代复现、实际/期望行为或源码根因。

### 只读入口

```bash
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py select --bug-id 123 --json
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py snapshot --bug-id 123 --json
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py compare --bug-id 123 --baseline-file <snapshot.json> --json
```

选择器支持 Bug ID、人员、产品/项目/执行、数值 module ID、状态/优先级/严重程度及可识别的创建/更新时间条件；结果会保留完整性、分页失败、缺字段和 `pending_queue`。`pending_queue` 不会自动继续。

### 授权边界

- `ANALYZE_ONLY`：只读取 ZenTao 与业务仓库并给出证据分类。
- `LOCAL_FIX_ALLOWED`：允许在证据充分时修改和验证业务代码，但不写 ZenTao。
- `RESOLVE_R2_ALLOWED`：只有当前用户明确要求生命周期 resolve，并且 workflow 的全部证据、验证、diff、并发复查和账号门槛通过时，才允许调用基础 `zentao` CLI 一次并回读。

“处理 Bug”最多推断为 `LOCAL_FIX_ALLOWED`，不等于 resolve 授权。`UNCLEAR`、`NO_CODE_EVIDENCE` 不得修改代码；`BLOCKED` 不得绕过门槛写入。

### 固定流程与禁区

`select → current Bug snapshot → 详情/资源证据 → 业务仓库约束与 git status → 源码证据/分类 → 最小修改与真实验证 → 写前 compare → 明确 R2 下一次 bug resolve → 显式回读`。

详细状态机、证据门、`will-not-fix` 信息退回分支、并发和错误规则见 [`references/workflow.md`](references/workflow.md)。生命周期 comment 模板见 [`references/comment-templates.md`](references/comment-templates.md)。

普通证据流程不得自动 close、activate、delete、连续处理下一 Bug、提交/推送/合并/部署，也不得用生命周期动作伪造 standalone comment 或 active Bug 单独转派。

## 两条路径共用的写入边界

resolver Python 脚本只做 ZenTao 读取和确定性处理；生命周期写入属于 Agent 编排，必须回到基础 `zentao` CLI。每个 eligible Bug 至多一次 resolve 命令，随后显式回读。基础 CLI 的 401 认证刷新合同不变；workflow 不增加重试，不绕过风险授权。
