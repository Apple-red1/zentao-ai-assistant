# 架构

当前合同入口：[`docs/current-contract.md`](current-contract.md)。本仓库是面向 AI 的 ZenTao 项目管理 Skill 集合。

## API 基础层

```text
用户 / AI
  -> skills/zentao/SKILL.md
  -> scripts/zentao.py
  -> cli/<resource>
  -> services/<resource>
  -> internal/zentao/<resource>.py
  -> internal/zentao/session.py
  -> internal/http/client.py
  -> ZenTao API v2
```

API endpoint 保持显式实现，`endpoints.json` 不参与运行时路由。

## Skill 职责

| Skill | 职责与边界 |
|---|---|
| `zentao` | 官方 API v2 的原子读取、写入、认证、资源获取和 CLI 安全合同；是所有 ZenTao 写入的唯一公开入口。 |
| `zentao-statistics` | 对支持的资源做确定性统计、聚合和同类范围比较；只读。 |
| `zentao-personal` | 聚合当前/指定用户的待办、风险、工作列表和摘要；只读，不把工作量当作绩效结论。 |
| `zentao-project-management` | 聚合 Project / Execution 的进度事实、风险信号和工作量分布；只读，不臆造健康分或绩效结论。 |
| `zentao-bug-resolver` | 以 Bug 为单位执行证据驱动的选择、快照、代码证据、最小修复与验证编排；resolver script 只读，生命周期写入由 Agent 回到基础 CLI。 |

统计、个人和项目管理脚本负责确定性分页、去重和聚合，向上保留 `complete` 与 `partial_failures`。Bug resolver 同样保留读取完整性和不可用字段；它的业务证据与本地修复属于 Agent 工作流，不扩展 API endpoint surface。

## 高层 Skill 读取链路

```text
zentao-statistics ---------┐
zentao-personal -----------+--> skills/_shared/zentao
zentao-project-management -┘        |
                                     v
                              zentao_skill.public
                                     |
                                     v
                               existing Services
                                     |
                                     v
                               ZenTao API v2
```

`zentao_skill.public` 是仓库内部稳定 programmatic facade，用于在一个 Python 进程内复用 Session 和完整分页。高层 Skill 禁止直接访问 `internal/zentao` / `internal/http`。

## Bug resolver 工作流链路

```text
zentao_bug_resolver.py
  select / snapshot / compare
        |
        v
skills/_shared/zentao -> zentao_skill.public（只读） -> existing Services -> ZenTao API v2

Agent 普通流程读取 resolver JSON 与业务仓库
  -> 证据分类 / 必要的最小本地修复 / 真实验证
  -> 写前 compare（只读并发复查）
  -> 基础 zentao CLI 的一次 R2 bug resolve
  -> 显式 snapshot 或 bug view 回读
```

普通流程的 `compare` 只比较起始 snapshot 与当前 Bug 的关键可观察字段，用于写前发现并发变化；它不是 CAS、ETag、锁或强一致保证。`changed=true`、比较失败或关键字段不可安全比较时停止写入；即使 `changed=false`，Agent 仍须遵守 R2 授权、证据、验证和 CLI 安全门槛。resolver script 不执行任意 shell、业务仓库写入或 ZenTao lifecycle；一次 R2 resolve 只能回到基础 `zentao` CLI。

`HUMAN_ATTESTED_RESOLVE` 由 Agent 执行：当前消息明确确认已解决且目标唯一 → 最小 bug view → active 时一次基础 CLI fixed resolve → 显式 bug view 回读。已 resolved/closed 不重复写；当前消息明确列出的 ID 严格串行，真实阻塞或 UNKNOWN_WRITE_RESULT 停止整个队列。

人工确认默认 `--resolved-build trunk`，用户明确值覆盖；默认不传 assignee/resolved-date，自动生成 HUMAN-ATTESTED 备注。跳过业务审计与 select/snapshot/compare，不增加 Python 写入编排器，不扩展 facade、endpoint 或普通流程的 pending 授权。

## 临时运行数据

```text
.tmp/zentao/auth/               # 短期 Token cache
.tmp/zentao/statistics/         # 可选统计中间数据
.tmp/zentao/personal/           # 可选个人聚合中间数据
.tmp/zentao/project-management/ # 可选项目聚合中间数据
.tmp/zentao/bug-resolver/       # Agent 生成的逐 Bug 人工确认备注
.tmp/zentao-resources/          # 对象附件/富文本资源
```

所有 `.tmp` 数据都被 Git 忽略。Token cache 是性能优化，不是新的凭据事实源；失效时回到 `/users/login`。

## 程序化 facade 安全边界

`zentao_skill.public` 是仓库内高层 Skill 的只读 facade，只暴露 list/view 类读取。写操作仍由 `zentao` CLI 承担，避免高层 Skill 绕过 delete `--yes` 等 CLI 安全合同。
