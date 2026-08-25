# AGENTS.md

本文件适用于整个仓库。自动化代理、AI 编码助手及人工维护者在修改本项目时，应先阅读本文件，再阅读与任务相关的源码、测试与文档。

## 1. 项目定位

本仓库交付的是单一 `zentao` Skill：

```text
skills/zentao/
```

它通过 Python 标准库直接调用 ZenTao 官方 API v2。最终产品形态不包含 MCP Server、独立 `src/zentao_ai/` 应用、系统级 `zentao-ai` 命令或第三方 Python 运行时依赖。

当前公开入口只有：

```bash
python skills/zentao/scripts/zentao.py <resource> <action> [scope] [parameters] --json
```

项目当前能力目录覆盖 20 个资源、120 个 ZenTao API v2 endpoint。若后续能力数量发生变化，相关 catalog、测试和文档必须同步更新，不能只修改其中一处。

## 2. 开始修改前必须阅读

按任务范围至少阅读：

1. `docs/current-contract.md`：当前唯一权威入口及各类事实来源的职责索引。
2. `skills/zentao/SKILL.md`：Skill 的用户侧调用契约、授权等级、输出和错误语义。
3. `skills/zentao/references/api-v2/<resource>.md`：目标资源的 API v2 能力说明。
4. `skills/zentao/references/api-v2/endpoints.json`：机器可读的 endpoint 覆盖与兼容性索引，仅用于审计和测试集合一致性。
5. `skills/zentao/RULES.md`：仅作为 ARCHIVED 历史迁移快照阅读，不得当作当前规则。
6. 目标实现及其对应测试。不要只看文档就修改代码，也不要只看单个模块推断完整调用链。

涉及发布、安全、配置或兼容性时，还应分别阅读：

- `docs/release-checklist.md`
- `docs/security.md`
- `docs/configuration.md`
- `docs/acceptance/zentao-21.7.8.md`

## 3. 事实来源与变更原则

- 当前仓库源码和测试是判断“现在如何实现”的事实依据。
- ZenTao API v2 契约是设计 endpoint 行为的目标基线。不得根据旧项目习惯臆造官方不存在的接口或字段。
- `endpoints.json` 是覆盖/审计 catalog，禁止把它改造成运行时万能 HTTP 路由表。
- 真实 ZenTao 实例的兼容性结论只能来自真实运行证据。Fake ZenTao 测试通过不能证明某个真实版本支持对应行为。
- `docs/acceptance/` 只记录实际验收观察；没有真实实例证据时，不得把兼容状态写成 `observed`。
- 不得把计划中的修改、未运行的测试或未验证的兼容性描述成已经完成。

## 4. 架构与依赖边界

固定调用链：

```text
用户 / AI
  -> skills/zentao/SKILL.md
  -> scripts/zentao.py
  -> cli/<resource>/commands.py
  -> services/<resource>/service.py
  -> internal/zentao/<resource>.py
  -> internal/zentao/session.py
  -> internal/http/client.py
  -> ZenTao API v2
```

依赖只能向下：

```text
entry -> cli -> services -> internal/zentao -> internal/http
```

同时允许 CLI 使用 `cli/output.py` 和 `cli/presenters/`，Internal 使用 `internal/config.py`、`internal/errors.py` 等内部基础设施。

禁止以下实现方式：

- `cli` 或 `services` 直接调用 `urllib`；
- `cli` 或 `services` 拼接 `/api.php/v2` URL；
- `internal/http` 了解 Bug、Story、Task 等领域语义；
- `internal/zentao` 反向依赖 CLI；
- presenter 调用 service；
- 为了方便重新引入 MCP、第三方 HTTP/CLI/配置库或动态 endpoint 路由。

Python 版本为 3.11+，运行时和测试均应仅使用标准库。

## 5. Endpoint 变更必须完整传播

新增、删除或修改一个 ZenTao endpoint 时，不要只改一个层。至少检查并按实际影响同步以下位置：

- `skills/zentao/references/api-v2/endpoints.json`
- 对应 `skills/zentao/references/api-v2/<resource>.md`
- `internal/zentao/<resource>.py` 的显式 API adapter
- `services/<resource>/service.py`
- `cli/<resource>/commands.py`
- Fake ZenTao 对应 resource/route
- contract tests
- CLI E2E tests
- coverage set / repository contract tests
- 必要的 Skill scenario tests
- 受影响的 README、features、testing、release checklist 或 acceptance 文档

每个运行时 endpoint 应保持显式实现。不要通过读取 `endpoints.json` 动态生成业务请求。

## 6. CLI 与调用语义

- 参数合同以实际 CLI `--help` 为准；修改参数时同步测试和资源 reference。
- 一条 CLI 命令只执行一个明确业务 endpoint。
- 不做“写后自动 GET”、自动第二次写或隐式业务动作。
- CLI 参数/用法错误返回 exit code `2`，并且在输入不合法时不应发出业务 HTTP 请求。
- `--json` 成功时 stdout 只输出领域 JSON；失败时 stdout 为空，stderr 输出稳定的 error JSON。
- 运行/API/认证/网络类错误使用 exit code `1`；Ctrl+C 使用 `130`。

## 7. 写入、删除与网络错误安全

风险等级遵循 `skills/zentao/SKILL.md`：

- R0 Read：`list` / `view`。
- R1 Normal Write：`create` / `edit` / `upload` / `change`。
- R2 Lifecycle：`resolve` / `close` / `activate` / `start` / `finish` 等状态变更。
- R3 Destructive：`delete`。

实现和测试必须保持以下安全合同：

- POST / PUT / DELETE 不自动重试。
- 写请求可能已执行但无法确认结果时返回 `UNKNOWN_WRITE_RESULT`。
- 收到 `UNKNOWN_WRITE_RESULT` 后不自动重放原请求，也不自动 GET；需要后续操作时，先由调用者显式执行只读确认。
- DELETE 必须同时具备用户明确删除意图和 CLI `--yes`；缺少 `--yes` 时必须在发送业务 HTTP 前拒绝。
- GET 仅可按既有实现对临时网络故障和 `502/503/504` 做有限重试；不要扩大到写操作。

## 8. 配置与敏感信息

本地配置只使用项目根目录 `.env` 与同名环境变量：

```text
ZENTAO_BASE_URL
ZENTAO_ACCOUNT
ZENTAO_PASSWORD
```

规则：

- 环境变量优先于 `.env`。
- `.env` 不提交；`.env.example` 必须保留为无真实秘密的模板。
- Token 通过 `POST /api.php/v2/users/login` 获取，只存在当前 Python 进程内存中。
- 不新增 token 文件、keyring、凭据数据库或第二套配置系统。
- 密码、Token、Cookie、Authorization Header 以及同类敏感字段不得出现在日志、错误详情、测试快照或文档示例中。
- 修改输出或错误处理时，应保留递归脱敏能力。

## 9. 测试要求

完整自动化测试入口：

```bash
python skills/zentao/tests/run_all.py
```

发布级本地门槛要求所有能力集合与 catalog 精确一致，并最终输出：

```text
Catalog:           120 / 120
Internal:          120 / 120
CLI:               120 / 120
Skill routes:      120 / 120
Fake API:          120 / 120
Contract tests:    120 / 120
CLI E2E:           120 / 120
Real API calls:      0
Result: PASS
```

如果 catalog 数量以后合法变化，上述各集合必须一起变化并继续保持精确一致。

测试原则：

- 优先为行为变化补最小失败测试，再修改实现。
- Fake ZenTao 在合同/E2E 前保持确定性重置。
- 自动化测试不得登录或访问真实 ZenTao。
- Build、import 成功或 Fake 测试不能替代目标行为验证。
- 真实实例测试需要显式环境和授权，并与默认自动化测试隔离。

## 10. 文档同步与防漂移

代码行为、CLI、endpoint catalog 或安全语义变化时，应检查相关文档是否需要同步。重点保持以下内容一致：

- `README.md` 的产品定位、入口和能力概览；
- `skills/zentao/SKILL.md` 的调用与风险合同；
- `docs/current-contract.md` 的当前合同入口及其指向的事实来源；
- `skills/zentao/references/api-v2/` 的资源说明与 catalog；
- `docs/architecture.md` 的真实分层；
- `docs/testing.md` 与 `docs/release-checklist.md` 的实际测试门槛；
- `docs/security.md` 的当前错误、安全与重试语义；
- `docs/acceptance/` 中有真实证据支撑的兼容性结论。

如果发现文档与实现冲突，应先以源码、测试和明确的当前决策确认事实，再修正文档；不要通过修改实现去迁就明显过期的历史描述。

## 11. 修改完成后的自检

提交或交付前至少完成：

```bash
python skills/zentao/tests/run_all.py
```

并检查：

- 没有引入第三方 Python 依赖；
- 没有新增 MCP 或独立应用入口；
- 没有跨层依赖或动态 endpoint 路由；
- endpoint 变更已完整传播；
- 没有泄露 `.env`、密码、Token、Cookie 或认证 Header；
- 写入、重试、`UNKNOWN_WRITE_RESULT` 与 delete `--yes` 语义未被弱化；
- Fake 结果没有被描述成真实 ZenTao 兼容性结论；
- 相关文档与当前行为保持一致；
- 没有遗留 `__pycache__`、临时文件、调试输出或本地凭据。

如果无法运行某项测试或验证，应在交付说明中明确写出未执行原因，不得宣称通过。
