# AGENTS.md

本文件适用于整个仓库。自动化代理、AI 编码助手及人工维护者在修改本项目时，应先阅读本文件，再阅读与任务相关的源码、测试与文档。

## 1. 项目定位

本仓库交付一组供 AI 使用的 ZenTao 项目管理 Skills：

```text
skills/zentao/                    # ZenTao API v2 原子能力
skills/zentao-statistics/         # 统计、聚合、范围对比
skills/zentao-personal/           # 个人待办、风险和工作摘要
skills/zentao-project-management/ # Project / Execution 管理分析
skills/zentao-bug-resolver/       # Bug 证据驱动分析、修复编排和受控 resolve
```

`zentao` 是基础能力层，继续通过 Python 标准库访问 ZenTao 官方 API v2；高层 Skill 组合只读能力形成项目管理信息。后续可以增加新的高层 Skill，但不得把同一职责复制到多个 Skill。

`zentao-bug-resolver` 提供普通证据流程与 `HUMAN_ATTESTED_RESOLVE` 人工确认分支：resolver script 只做 Bug 选择、快照、写前比较等确定性读取，Agent 在普通流程负责业务仓库证据、最小本地修复与验证；需要一次 R2 lifecycle resolve 时只能回到基础 `zentao` CLI。

API CLI 公开入口保持：

```bash
python skills/zentao/scripts/zentao.py <resource> <action> [scope] [parameters] --json
```

仓库内高层 Skill 需要复用同一个 Session 时，应使用 `zentao_skill.public` programmatic facade，不直接依赖 `internal/**`。

## 2. 开始修改前必须阅读

按任务范围至少阅读：

1. `docs/current-contract.md`：当前唯一权威入口。
2. 目标 Skill 的 `SKILL.md`。
3. 涉及 API 时读取 `skills/zentao/SKILL.md`、对应 API reference 与 `endpoints.json`。
4. `skills/zentao/references/programmatic.md`：高层 Skill 调用 API 基础层的程序化合同。
5. 目标实现及对应测试。
6. `skills/zentao/RULES.md` 只作为 ARCHIVED 历史迁移快照，不得当作当前规则。

涉及发布、安全、配置或兼容性时，还应阅读 `docs/release-checklist.md`、`docs/security.md`、`docs/configuration.md` 和相应 acceptance 文档。

## 3. 事实来源与变更原则

- 当前源码和测试是“现在如何实现”的事实依据。
- ZenTao API v2 契约是 endpoint 行为目标基线；真实版本兼容性只能来自真实运行证据。
- `endpoints.json` 是 API 覆盖/审计 catalog，不是运行时万能路由表。
- 高层统计、个人和项目管理能力必须基于实际返回数据，不得臆造字段、历史趋势、健康分或绩效结论。
- 计划中的修改、未运行的测试、未验证的兼容性不得写成已完成。

## 4. 架构与依赖边界

API Skill 固定链路：

```text
zentao Skill / CLI
  -> cli
  -> services
  -> internal/zentao
  -> internal/http
  -> ZenTao API v2
```

高层 Skill 链路：

```text
zentao-statistics / zentao-personal / zentao-project-management
  -> skills/_shared/zentao
  -> zentao_skill.public
  -> zentao Services
  -> internal/zentao
  -> internal/http
```

Bug resolver 的读取与写入编排链路：

```text
zentao_bug_resolver.py (select / snapshot / compare，只读)
  -> skills/_shared/zentao
  -> zentao_skill.public（只读）
  -> zentao Services
  -> internal/zentao
  -> internal/http
  -> ZenTao API v2

Agent 普通流程：读取证据 + 业务仓库最小修复/验证
  -> 写前 compare（只读复查，不是 CAS/ETag/锁）
  -> 基础 zentao CLI 的一次 R2 bug resolve
  -> 显式 snapshot / bug view 回读
```

禁止：

- 高层 Skill 自己拼 `/api.php/v2` URL 或直接使用 `urllib`；
- 高层 Skill import `zentao_skill.internal.*` 或直接绕过 API Skill 安全合同；
- `zentao-bug-resolver` script 执行 lifecycle 或写入；Agent 的一次 R2 resolve 只能调用基础 `zentao` CLI，不能改走 facade、私有接口或替代 endpoint；
- 将 resolver 的 `compare` 当作 CAS、ETag、锁或强一致写入保证；它只是写前的只读并发复查；
- `cli`/`services` 直接使用 HTTP；
- 恢复 MCP、独立系统级 `zentao-ai` 应用或第三方 Python 运行时依赖；
- 通过读取 `endpoints.json` 动态生成业务请求。

Python 版本为 3.11+，运行时和测试只使用标准库。

## 5. API endpoint 变更

API endpoint 新增、删除或修改时，必须完整传播 `endpoints.json`、resource reference、Internal adapter、Service、CLI、Fake、contract、CLI E2E 和必要文档。API surface 仍必须保持 catalog 与各实现集合精确一致。

API endpoint 覆盖率只描述 `zentao` 基础 Skill，不能当作整个多 Skill 仓库的功能覆盖率。

## 6. 高层 Skill 开发规则

- 高层 Skill 按“AI 要完成的项目管理任务”拆分，不按 API 资源重复拆 Skill。
- 数字、去重、分页、日期分类等确定性工作优先由 Python 脚本完成，AI 只解释结果。
- 可复用的低层分页、身份、临时数据能力放 `skills/_shared/zentao/`；有业务含义的算法留在所属 Skill。
- `partial_failures`、`complete`、截断或分页异常必须向上保留，不能把不完整数据展示成完整事实。
- 高层 Skill 默认只读；需要写操作时转到 `zentao` 的明确 API 能力和风险授权规则。
- `zentao-bug-resolver` 的脚本只通过 `zentao_skill.public` 读取；普通流程的 Agent 只有在证据、验证、diff、并发复查和授权门槛全部满足时，才可把一次 R2 resolve 回交基础 CLI。
- resolver 的 `compare` 是写入前复查；`changed=true`、比较失败或关键事实不可安全比较都必须阻止写入，`changed=false` 也不提供 CAS/ETag/锁保证。

## 7. CLI 与写入安全

`zentao` 的 CLI / 错误 / 风险合同保持：

- R0 Read：list/view；R1 Normal Write；R2 Lifecycle；R3 delete。
- 一条 API CLI 命令只执行一个明确 endpoint。
- POST/PUT/DELETE 不对网络失败自动重试；结果不确定返回 `UNKNOWN_WRITE_RESULT`。
- DELETE 需要用户明确删除意图并传 `--yes`。
- 明确 401 表示认证拒绝，允许清理临时 Token、重新登录并重放该次被 401 拒绝的请求一次；这不属于网络错误重试。

## 8. 配置、Token 与 `.tmp`

长期连接配置只使用根目录 `.env` 与同名环境变量：

```text
ZENTAO_BASE_URL
ZENTAO_ACCOUNT
ZENTAO_PASSWORD
```

Token 通过 `/users/login` 获取。为减少多个 Skill/进程重复登录，允许将短生命周期 Token 缓存在：

```text
.tmp/zentao/auth/
```

规则：

- `.tmp/` 必须 Git ignore；不得把 Token 写入 `.env`、仓库文件、日志或测试快照。
- Token cache 按 base URL + account 隔离，不保存密码；默认本地 TTL 8 小时。
- POSIX cache 目录 `0700`、文件 `0600`。
- 缓存无效/过期时删除并重新登录；服务端 401 可触发一次认证刷新。
- 高层 Skill 的大批量中间数据也可以落到 `.tmp/zentao/<skill>/`；这些文件属于临时运行数据，不得成为长期事实源。

对象附件仍按 `resource fetch` 既有规则落到 `.tmp/zentao-resources/`。

## 9. 测试要求

仓库级完整自动化入口：

```bash
python tests/run_all.py
```

API Skill 的 120 endpoint 专项门槛仍为：

```bash
python skills/zentao/tests/run_all.py
```

并继续要求 Catalog/Internal/CLI/Skill routes/Fake/Contract/CLI E2E 精确 `120/120`、`Real API calls: 0` 和 `Result: PASS`。

高层 Skill 至少覆盖：完整分页、重复 ID、空数据、部分失败、用户重名、日期边界、稳定排序、数据完整性和各自核心用户场景。自动化测试不得访问真实 ZenTao。

## 10. 文档同步与防漂移

重点保持 `README.md`、各 Skill `SKILL.md`、`docs/current-contract.md`、`docs/architecture.md`、`docs/testing.md`、`docs/security.md`、`docs/configuration.md` 与源码一致。历史 Issue / RULES 不得覆盖当前合同。

## 11. 修改完成后的自检

交付前至少执行：

```bash
python tests/run_all.py
```

并确认：无第三方依赖、无 MCP、无高层 Skill 直连 HTTP、无 Token/密码泄露、无遗留 `__pycache__`/调试输出、Patch 可回放。无法运行的检查必须明确说明。

### 程序化 facade 写入边界

程序化 facade 只读。高层 Skill 不得通过 facade 执行 create/edit/lifecycle/delete；需要写入时必须回到 `zentao` 的公开 CLI 和既有风险合同。resolver script 永远不执行 lifecycle；Agent 的一次 R2 resolve 只能调用基础 CLI 一次，随后显式回读。

### 人工确认解决分支

`HUMAN_ATTESTED_RESOLVE` 只在当前用户明确确认已解决且目标唯一时触发，该消息即对应 Bug 的 R2 授权。不读取业务仓库、源码、提交、测试、diff、附件或 patch，不运行 select/snapshot/compare；普通证据门槛不适用。只做最小 bug view，active 时一次基础 CLI fixed resolve，再显式 bug view 回读；resolved/closed 不重复写。

默认显式 `--resolved-build trunk`，用户明确指定其它值时覆盖；默认不传 assignee/resolved-date，自动生成 HUMAN-ATTESTED 备注，不伪造审计事实。当前消息明确列出的多个 Bug 按输入顺序去重并严格串行，任一真实阻塞立即停止；`UNKNOWN_WRITE_RESULT` 停止整个队列、绝不重试，只读回读。不自动 close/activate/delete 或用其它 endpoint 绕过失败。resolver script 和 facade 保持只读。
