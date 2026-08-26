# ZenTao AI 项目管理 Skills 当前合同入口

> 状态：**CURRENT / 当前唯一权威入口**
> 更新日期：2026-08-26
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
- `pending_queue` 只记录待处理 ID，不自动继续；下一项必须由用户再次明确继续，并重新解析授权与起始 snapshot。
- 程序化 facade 对所有高层 Skill 只读；Bug resolver 的 R2 生命周期写入不能由脚本或 facade 执行，必须在当前用户明确授权、证据/验证/写前 compare 门槛全部满足后回到基础 `zentao` CLI。
- Bug resolver 使用 `ANALYZE_ONLY`、`LOCAL_FIX_ALLOWED`、`RESOLVE_R2_ALLOWED` 三个授权等级，以及 `SOLVABLE`、`UNCLEAR`、`NO_CODE_EVIDENCE`、`BLOCKED` 四类证据结论；一次任务只处理一个当前 Bug，pending 项不继承授权。
- 只有 `SOLVABLE` 的完整证据、验证、diff 和写前 compare 门槛满足后，Agent 才能经基础 `zentao` CLI 执行一次 `bug resolve` 并显式回读；不会自动 close、activate、delete，也不把生命周期动作当作 standalone comment 或 active Bug 单独转派。
- 信息不足的 `UNCLEAR` / `NO_CODE_EVIDENCE` 不修改业务代码；`will-not-fix` 仅表示按门槛退回补充信息，不是技术修复结论。
- 当前不宣称 module 名称映射、Bug 历史、ETag 或其它未经真实证据验证的字段/接口。
- R3 delete 仍要求用户明确删除意图与 `--yes`；写请求网络失败不自动重试，未知结果使用 `UNKNOWN_WRITE_RESULT`。
- Token 允许短期缓存到 `.tmp/zentao/auth/`；不写回 `.env`，不保存密码。明确 401 会清理缓存并重新登录一次。
- `.tmp/zentao/<skill>/` 可保存临时聚合数据，但不是长期事实源。

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
