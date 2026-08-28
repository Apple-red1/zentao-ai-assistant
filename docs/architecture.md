# 架构

当前合同入口：[`docs/current-contract.md`](current-contract.md)。本仓库是面向 AI 的 ZenTao 项目管理 Skill 集合。

## 双入口与 canonical source

```text
Project instructions / Host manifests
        ↓
canonical SKILL.md + scripts
        ↓
public facade / runtime bridge
        ↓
Services / RuntimePaths
        ↓
ZenTao API v2 / user data roots
```

根目录 `plugin.json` 是 portable manifest；`.claude-plugin/plugin.json`、
`.claude-plugin/marketplace.json` 和 `.codex-plugin/plugin.json`、
`.agents/plugins/marketplace.json` 只是宿主适配元数据。Plugin adapter 不进入
业务层，也不复制 `skills/`；Clone 的 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md` 只
负责项目指令路由。

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
| `zentao-batch-export` | 按显式 `type:id` 批量导出多个对象的完整字段与资源，生成 manifest 和动态 ZIP；只读，复用基础 CLI 的 `view/resource fetch`。 |

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

`zentao-batch-export` 的业务含义在自己的 `scripts/`：它通过基础 `zentao.py` CLI 串行调用单对象 `view` 与 `resource fetch`，不复制资源发现/下载实现；同时只调用 public runtime bridge 取得当前 scope 临时根目录。最终资料位于 `zentao/zentao-batch-export/<run-id>/staging/`，ZIP 使用动态文件名，资源复制时再次拒绝符号链接和 trusted `zentao-resources` 目录外路径。

`zentao_skill.public.runtime` 只暴露按 RuntimePaths 安全创建/取得临时根目录的
runtime bridge，不是新的 ZenTao API，也不执行写入。RuntimePaths 统一决定
config/cache/tmp 三类路径；高层 Skill 仍只能通过 public facade，不能 import
`internal` 或直连 HTTP。

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

## RuntimePaths 与临时运行数据

```text
project config: <repo>/.env
project cache:  <repo>/.tmp/zentao/auth/
project temp:   <repo>/.tmp/zentao/<skill>/, <repo>/.tmp/zentao-resources/

user config:    ~/.zentao-ai-assistant/config.env
user cache:     ~/.zentao-ai-assistant/cache/auth/
user temp:      ~/.zentao-ai-assistant/tmp/zentao/<skill>/,
                ~/.zentao-ai-assistant/tmp/zentao-resources/
```

高层临时材料中的 `<skill>` 包括 `statistics`、`personal`、`project-management`
和 `bug-resolver`；后者可保存 Agent 生成的逐 Bug 人工确认备注。

RuntimePaths 先按 `ZENTAO_CONFIG_FILE`、仓库根 `.env`、Home config 选择一个配置
源；环境变量覆盖所选文件，不跨文件补字段。项目 `.tmp` 与用户 runtime `tmp`
都只保存临时材料。Token cache 是性能优化，不是新的凭据事实源；失效时回到
`/users/login`。所有目录及 Token/config 文件继续遵守 `0700` / `0600` 权限目标。

## 程序化 facade 安全边界

`zentao_skill.public` 是仓库内高层 Skill 的只读 facade，只暴露 list/view 类读取。写操作仍由 `zentao` CLI 承担，避免高层 Skill 绕过 delete `--yes` 等 CLI 安全合同。
