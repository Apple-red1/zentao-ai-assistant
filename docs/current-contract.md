# ZenTao AI 项目管理 Skills 当前合同入口

> 状态：**CURRENT / 当前唯一权威入口**
> 更新日期：2026-08-27
> 适用范围：仓库内所有 ZenTao Skills、API v2 基础能力、共享脚本、测试和发布检查。

本页是“现在应该相信什么”的索引。历史设计文档只用于追溯，不能覆盖本页指向的当前源码、测试与合同。

## 当前 Skill 集合

| Skill | 当前职责 |
|---|---|
| `skills/zentao/` | ZenTao 官方 API v2 原子读取/写入、认证、资源获取和安全合同 |
| `skills/zentao-statistics/` | 确定性统计、聚合和同类范围对比 |
| `skills/zentao-personal/` | 当前/指定用户的待办、风险、工作列表和工作摘要 |
| `skills/zentao-project-management/` | Project / Execution 的进度事实、风险信号和工作量分布 |
| `skills/zentao-bug-resolver/` | 证据驱动的 Bug 只读 `select` / `snapshot` / `compare` 与 Agent 编排 |

共享低层辅助位于 `skills/_shared/zentao/`，它没有 `SKILL.md`，不参与 Skill 路由。

当前公开 surface 为 5 Skills，且只有仓库根目录的这一份 `skills/` 是 canonical
业务能力源。Clone 与 Plugin 入口共用相同 Skill 文件：

```text
Clone:  AGENTS.md；Claude/Gemini 分别由 CLAUDE.md / GEMINI.md 薄引用
Plugin: plugin.json / .claude-plugin / .codex-plugin -> 根目录 skills/
```

Clone 使用 project scope；Plugin 使用 user scope。当前运行合同称为
project/user scope：项目配置为 `<repo>/.env`，用户配置为
`~/.zentao-ai-assistant/config.env`。配置选择严格为
`ZENTAO_CONFIG_FILE` → 仓库根 `.env`（存在时）→ Home config，环境变量只覆盖
所选文件，不跨文件补字段。

支持边界：

| Surface | 当前合同 |
|---|---|
| Clone + Codex | supported，通过 `AGENTS.md` |
| Clone + Claude Code | supported，通过 `CLAUDE.md` |
| Clone + Gemini CLI | supported，通过 `GEMINI.md` |
| Claude Code Plugin | v1 formal support target；Claude Code verified gate 必须在发布前真实通过 |
| Codex Plugin | v1 formal support target；Codex verified gate 必须在发布前真实通过 |
| Gemini Plugin | Gemini Plugin not v1 |
| Cursor/Copilot/VS Code Plugin | Cursor/Copilot/VS Code unverified |

静态 manifest 或自动化测试不能代替 Claude/Codex verified gate；宿主不可用时必须
记录 `BLOCKED_ENVIRONMENT`，不得把 Plugin 支持写成已完成。

## 权威文件及职责

| 范围 | 当前事实来源 |
|---|---|
| API Skill 用户调用、风险和输出 | `skills/zentao/SKILL.md` |
| 高层 Skill 调用 | 各自 `SKILL.md` |
| Bug 证据驱动流程、授权和生命周期边界 | `skills/zentao-bug-resolver/SKILL.md` 与 `skills/zentao-bug-resolver/references/workflow.md` |
| 高层 Skill → API 基础层程序化合同 | `skills/zentao/references/programmatic.md` |
| endpoint method/path/参数/兼容元数据 | `skills/zentao/references/api-v2/endpoints.json` |
| 独立官方 API v2 evidence | `skills/zentao/references/api-v2/official-contract.json` |
| 真实 ZenTao 21.7.8 观察 | `skills/zentao/references/compatibility/zentao-21.7.8.json` 与 `docs/acceptance/zentao-21.7.8.md` |
| 工程约束、分层、安全和交付门槛 | `AGENTS.md` |
| 目录职责 | `docs/architecture.md` |

`skills/zentao/RULES.md` 是 ARCHIVED 历史迁移快照。

## 当前实现事实

- `zentao` API catalog 仍覆盖 20 个资源、**120 个 ZenTao API v2 endpoint**，API 实现、CLI、Skill 路由、Fake、合同和 CLI E2E 保持 `120/120`。
- 高层 Skill 不改变 endpoint catalog，也不把 API 组合能力冒充官方 endpoint。
- 高层 Skill 通过 `zentao_skill.public` 复用现有 Services/Session，不直接访问 `internal/http` 或拼接 API URL。
- `zentao-bug-resolver` 是第四个高层 Skill：其脚本只做证据驱动的只读 `select`、`snapshot`、`compare`，通过 `zentao_skill.public` 的只读 facade 取数；Agent 负责基于结果编排业务仓库证据、最小修改、验证和写前复查。这些脚本操作不是新的 API endpoint，不新增、不计入基础 `zentao` 的 120 个 API endpoint。
- 统计、个人与项目管理的关键数量由脚本确定性计算；所有高层结果的 `complete/partial_failures` 必须保留。Bug resolver 还必须保留 `complete=false`、`pending_queue`、`unsupported_filters` 和 `unavailable_fields`；候选不完整时不得声称证据完整。
- 普通流程的 `pending_queue` 只记录待处理 ID，不自动继续；下一项必须由用户再次明确继续，并重新解析授权与起始 snapshot。
- 程序化 facade 对所有高层 Skill 只读；Bug resolver 的 R2 生命周期写入不能由脚本或 facade 执行，必须在当前用户明确授权、对应分支门槛满足后回到基础 `zentao` CLI。
- Bug resolver 普通流程使用 `ANALYZE_ONLY`、`LOCAL_FIX_ALLOWED`、`RESOLVE_R2_ALLOWED` 三个授权等级，以及 `SOLVABLE`、`UNCLEAR`、`NO_CODE_EVIDENCE`、`BLOCKED` 四类证据结论；一次任务只处理一个当前 Bug，pending 项不继承授权。
- 普通 fixed 分支只有 `SOLVABLE` 的完整证据、验证、diff 和写前 compare 门槛满足后，Agent 才能经基础 `zentao` CLI 执行一次 `bug resolve` 并显式回读；不会自动 close、activate、delete，也不把生命周期动作当作 standalone comment 或 active Bug 单独转派。
- 信息不足的 `UNCLEAR` / `NO_CODE_EVIDENCE` 不修改业务代码；`will-not-fix` 仅表示按门槛退回补充信息，不是技术修复结论。
- 当前不宣称 module 名称映射、Bug 历史、ETag 或其它未经真实证据验证的字段/接口。
- `HUMAN_ATTESTED_RESOLVE`：当前消息明确确认已解决且目标唯一，即人工结论与对应 Bug 的 R2 授权；最小 bug view → active 时一次 fixed resolve → 显式 bug view 回读。不读取业务仓库/源码/提交/测试/diff/附件/patch，不运行 select/snapshot/compare，不套用普通证据门槛。
- 人工确认默认显式 `--resolved-build trunk`，用户明确指定其它值时覆盖；默认不传 assignee/resolved-date，自动生成 `[CODEX-HUMAN-ATTESTED-RESOLUTION]` 备注，不伪造代码或测试事实。resolved/closed 不重复写；当前消息明确列出的多个 Bug 按输入顺序去重并严格串行；真实阻塞停止，`UNKNOWN_WRITE_RESULT` 停止整个队列、只读回读且绝不重试。仅在真实阻塞时提问，不自动 close 或切换 endpoint。
- “帮我解决/修复”与不确定表达不触发人工确认；人工确认是 Agent 指令分支，没有新增 Python lifecycle 编排器，不改变 120 endpoint 或只读 facade。
- R3 delete 仍要求用户明确删除意图与 `--yes`；写请求网络失败不自动重试，未知结果使用 `UNKNOWN_WRITE_RESULT`。
- project scope Token 允许短期缓存到 `.tmp/zentao/auth/`；user scope 使用
  `~/.zentao-ai-assistant/cache/auth/`；不写回配置文件，不保存密码。明确 401
  会清理缓存并重新登录一次。
- project scope 的聚合/资源临时数据位于 `.tmp/zentao/<skill>/` 与
  `.tmp/zentao-resources/`；user scope 位于
  `~/.zentao-ai-assistant/tmp/zentao/<skill>/` 与
  `~/.zentao-ai-assistant/tmp/zentao-resources/`。这些目录都不是长期事实源。
- 运行约束：`standard library only / no MCP`；不复制第二份 Skills，不把宿主
  Plugin cache 当作配置、Token 或持久数据目录。

## 测试入口

仓库级：

```bash
python tests/run_all.py
```

API endpoint 专项：

```bash
python3 skills/zentao/tests/run_all.py
```

API 专项仍必须输出各 surface `120/120`、`Real API calls: 0` 和 `Result: PASS`；高层 Skill 的单元/行为测试同样只使用标准库桩或本地 Fake，不访问真实 ZenTao；官方 evidence 与 21.7.8 compatibility 单独报告。

## 程序化访问边界

程序化 facade 只读；高层 Skill 的写操作不得绕过 `zentao` CLI 的既有安全合同。

风险等级不变：R0/R1/R2/R3；R3 delete 必须明确删除意图并带 `--yes`，写请求
不确定结果使用 `UNKNOWN_WRITE_RESULT`。Fake 自动化与真实 ZenTao 实例严格隔离。
