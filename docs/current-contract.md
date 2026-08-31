# ZenTao AI 项目管理 Skills 当前合同入口

> 状态：**CURRENT / 当前唯一权威入口**
> 更新日期：2026-08-31
> 适用范围：仓库内所有 ZenTao Skills、API v2 基础能力、共享脚本、测试和发布检查。

本页是“现在应该相信什么”的索引。历史设计文档只用于追溯，不能覆盖本页指向的当前源码、测试与合同。

## 当前 Skill 集合

| Skill | 当前职责 |
|---|---|
| `skills/zentao/` | ZenTao 官方 API v2 原子读取/写入、认证、资源获取和安全合同 |
| `skills/zentao-statistics/` | 确定性统计、聚合和同类范围对比 |
| `skills/zentao-personal/` | 当前/指定用户待办与摘要；个人默认团队名单、团队 Bug 与团队日报 |
| `skills/zentao-project-management/` | Project / Execution 的进度事实、风险信号和工作量分布 |
| `skills/zentao-bug-resolver/` | 证据驱动的 Bug 只读 `select` / `snapshot` / `compare` 与 Agent 编排 |
| `skills/zentao-batch-export/` | 多个 ZenTao 对象的完整 `view` 字段、资源与 ZIP 批量资料导出 |

共享低层辅助位于 `skills/_shared/zentao/`，它没有 `SKILL.md`，不参与 Skill 路由。

当前公开 surface 为 6 Skills，且只有仓库根目录的这一份 `skills/` 是 canonical
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
| 个人默认团队配置、查询与展示 | `skills/zentao-personal/references/team.md` |
| 所有 Skill 的聊天 Bug ID 展示 | `skills/zentao/references/bug-display.md` |
| Bug 证据驱动流程、授权和生命周期边界 | `skills/zentao-bug-resolver/SKILL.md` 与 `skills/zentao-bug-resolver/references/workflow.md` |
| 高层 Skill → API 基础层程序化合同 | `skills/zentao/references/programmatic.md` |
| endpoint method/path/参数/兼容元数据 | `skills/zentao/references/api-v2/endpoints.json` |
| 独立官方 API v2 evidence | `skills/zentao/references/api-v2/official-contract.json` |
| 真实 ZenTao 21.7.8 观察 | `skills/zentao/references/compatibility/zentao-21.7.8.json` 与 `docs/acceptance/zentao-21.7.8.md` |
| 工程约束、分层、安全和交付门槛 | `AGENTS.md` |
| 目录职责 | `docs/architecture.md` |

`skills/zentao/RULES.md` 是 ARCHIVED 历史迁移快照。

## 当前实现事实

- 插件版本 `1.10.0`，仍为六个正式 Skill。`zentao-personal` 提供 `team-view/add/remove/replace` 名单维护及 `team-bugs/team-brief` 查询入口；没有新增 API endpoint。
- 团队配置始终保存于 `~/.zentao-ai-assistant/teams/<identity-sha256>.json`，以规范化 base URL + account 隔离，跨源码项目复用；只接受明确的名单维护请求，完整用户目录唯一解析后保存真实 account，本人自动纳入而不保存为配置成员。损坏配置、身份冲突、目录不完整和并发写入均阻止覆盖。
- 团队 Bug 与日报共用完整分页、跨 Product/Project/Execution 扫描、ID 去重和阶段分类；`active` 按当前 `assignedTo` 归入“需要马上行动”，`resolved` 按 `resolvedBy` 归入“待测试验证”，当前 `assignedTo` 仅展示测试负责人，`closed` 排除。显式 scope 仅缩小查询。输出按阶段→成员→优先级/严重程度/旧 Bug/数值 ID 排序，全部成员和符合条件的 Bug 都保留；日报只增加汇总。
- 团队 `--markdown` 对 active 输出四列、对 resolved 输出含“当前测试负责人”的五列表格，并调用基础 `bug web-url` 生成编号链接；机器 JSON 与默认终端 JSON 保持原始字段。`resolvedBy` 无效不回退猜测；团队内解决人的测试负责人无效时仍保留 Bug。字段失败、未知状态、日期异常、冲突和分页截断通过 `complete/partial_failures` 暴露，失败不能伪装为 0。独立查询不构成事务快照。
- facade 新增只读 `connection_identity` 和可选 `list_all(preserve_partial=True)`；后者在页读取失败时保留已读页且不重试，默认调用行为不变。团队本地配置写入不扩展 facade 的 ZenTao 写入权限。
- `zentao` API catalog 仍覆盖 20 个资源、**120 个 ZenTao API v2 endpoint**，API 实现、CLI、Skill 路由、Fake、合同和 CLI E2E 保持 `120/120`。
- 高层 Skill 不改变 endpoint catalog，也不把 API 组合能力冒充官方 endpoint。
- `zentao-batch-export` 是只读批量资料编排：首版支持 `bug / epic / execution / feedback / product / product-plan / program / requirement / story / task / test-case / ticket / user`；输入显式使用 `type:id`，脚本按 `type + id` 去重。
- 批量导出不新增基础 API endpoint：每个对象调用现有 CLI `view` 与 `resource fetch`；`content.md` 以可读 Markdown 展示完整 `view --json` 字段，成功归档的富文本资源引用改为对象目录下的相对 `resources/<file>` 路径，资源进入 `objects/<type>/<id>/resources/`，根 `manifest.json` 仍只记录索引、完整性和完整失败信息。
- `resource fetch` 的 HTTP 200 资源还必须通过非空、明显 HTML 登录/错误页和 MIME
  类型一致性校验；不通过时使用 `RESOURCE_CONTENT_INVALID` 保留在
  `partial_failures`，旧式 `/index.php?...fileID=...` URL 按资源 ID/类型提示生成语义文件名。富文本旧式 `m=file&f=read` 图片请求仅将 `f` 改为同源 `download`，普通附件 URL 不改写，且输出保留原始 `source`。
- 独立评论是固定同源 Legacy Web 兼容能力，不新增官方 API endpoint；当前十种对象
  `bug / story / product / task / execution / project / test-task / product-plan / release / build`
  均支持评论、重复 `--file` 和重复 `--inline-image`。普通附件与内嵌图片可以在同一条评论中
  提交；同一调用内重复的本地图片复用远端 file identity，同时保留重复引用。用户正文先按
  HTML 实体编码，受控图片片段再追加为 markup。
- 独立评论写入严格执行写前 action snapshot、一次页面 POST、写后 action ID 差集和唯一候选
  回读确认；0 个或多个候选、关键对象字段变化或无法安全解析时不重放，并如实返回
  `UNKNOWN_WRITE_RESULT`/并发变化信息。Bug 内联图片先通过固定
  `/index.php?m=file&f=ajaxUpload&uid=...` 上传，响应异常时停止评论并标记潜在孤儿文件。
- `resource fetch --include-comments` 仅在显式开启时读取已验证的 Bug/Story comment action
  附件与允许的内嵌图片，并输出 `origin=comment`、`action_id` 等追溯元数据；批量导出对
  `bug`/`story` 自动使用该显式能力，其它对象保持默认资源范围。
- 21.7.8 的 `file.upload` v2 endpoint 仍按真实证据标记为 unsupported；Bug 的基础 CLI
  上传在检测到 v2 空响应后，会先回读确认是否已经落库，未落库时才使用固定的
  `bug/edit` 页面 `files[]` 表单兼容写入，并通过 API 详情回读确认附件。该兼容路径不
  接受任意页面 URL、不使用浏览器自动化，页面写入异常只回读一次且不盲目重试。
- Bug `create/edit` 的 `--steps-inline-image` 是不新增 endpoint 的页面兼容能力：先读取固定
  `bug/create` 或 `bug/edit` 表单，使用该表单 `uid` 通过同源 `file/ajaxUpload` 上传本地
  图片，再以受控 `<img src>` markup 随 `steps` 单次提交；用户步骤文本先 HTML 转义，图片
  顺序与重复引用保留。表单只按精确字段名 `uid` 受控读取，兼容 `hidden` 和真实页面的
  `text` 类型，不把其它可见输入加入 payload；uid 缺失、为空或出现冲突控件时继续
  fail-closed。表单能力、上传响应、同源 URL、步骤图片和 Bug 文件归属任一无法安全确认
  时停止；业务写入结果未知时不重试，仅按合同回读。该能力不写入评论/action。
- 当前消息包含聊天附件图片且用户要求图片进入 Bug 描述/重现步骤时，宿主必须把可读的本地
  附件路径传给同一次 `bug create/edit --steps-inline-image`；禁止调用 `bug comment`、
  `--inline-image` 或创建后补备注。无法取得可读本地路径时先阻塞，不创建语义不完整的 Bug；
  只有用户明确要求添加备注/历史记录时，才使用评论内嵌图片。Plugin 更新后需重新加载
  当前 canonical `skills/`，否则旧缓存不会包含该路由合同。
- 资源发现只处理当前附件区和业务富文本，不递归扫描 `actions`、`dynamics`、`history`、`diff`
  审计历史字段；`dynamics` 是 21.7.8 部分对象详情中的动态历史容器，不属于当前资源范围。
- 统计 `by_assignee` 将空值和 ZenTao 特殊值 `closed` 显式归入 `unassigned`，不作为真实负责人统计。
- 单对象/单资源失败不阻断后续导出；最终 ZIP 位于当前 scope 的 `.tmp/zentao/zentao-batch-export/<run-id>/` 或 `~/.zentao-ai-assistant/tmp/zentao/zentao-batch-export/<run-id>/`，文件名为动态 `zentao-export-<timestamp>-<short-id>.zip`，不接受调用方任意输出路径。
- 统计、个人、项目管理和 Bug resolver 的读取脚本通过 `zentao_skill.public` 复用现有 Services/Session；`zentao-batch-export` 通过 public runtime bridge 取得 scope 路径并组合基础 `zentao` CLI。所有高层 Skill 都禁止直接访问 `internal/http` 或拼接 API URL。
- `zentao-bug-resolver` 是第四个高层 Skill：其脚本只做证据驱动的只读 `select`、`snapshot`、`compare`，通过 `zentao_skill.public` 的只读 facade 取数；Agent 负责基于结果编排业务仓库证据、最小修改、验证和写前复查。这些脚本操作不是新的 API endpoint，不新增、不计入基础 `zentao` 的 120 个 API endpoint。
- 统计、个人与项目管理的关键数量由脚本确定性计算；所有高层结果的 `complete/partial_failures` 必须保留。Bug resolver 还必须保留 `complete=false`、`pending_queue`、`unsupported_filters` 和 `unavailable_fields`；候选不完整时不得声称证据完整。
- 普通流程的 `pending_queue` 只记录待处理 ID，不自动继续；下一项必须由用户再次明确继续，并重新解析授权与起始 snapshot。
- 程序化 facade 对所有高层 Skill 只读；Bug resolver 的 R2 生命周期写入不能由脚本或 facade 执行，必须在当前用户明确授权、对应分支门槛满足后回到基础 `zentao` CLI。
- Bug resolver 普通流程使用 `ANALYZE_ONLY`、`LOCAL_FIX_ALLOWED`、`RESOLVE_R2_ALLOWED` 三个授权等级，以及 `SOLVABLE`、`UNCLEAR`、`NO_CODE_EVIDENCE`、`BLOCKED` 四类证据结论；一次任务只处理一个当前 Bug，pending 项不继承授权。
- 普通 fixed 分支只有 `SOLVABLE` 的完整证据、验证、diff 和写前 compare 门槛满足后，Agent 才能经基础 `zentao` CLI 执行一次 `bug resolve` 并显式回读；不会自动 close、activate、delete，也不把生命周期动作当作 standalone comment 或 active Bug 单独转派。
- 信息不足的 `UNCLEAR` / `NO_CODE_EVIDENCE` 不修改业务代码；`will-not-fix` 仅表示按门槛退回补充信息，不是技术修复结论。
- 当前不宣称 module 名称映射、Bug 历史、ETag 或其它未经真实证据验证的字段/接口。
- `bug web-url` 按固定禅道路由本地生成链接，不是新的 API endpoint，不访问页面或打开浏览器。
- 所有六个 Skill 的聊天回复只要展示 Bug ID，编号本身就是可点击链接；统一消费 `bug web-url` 返回的 `id → url`，不按数组位置配对。不改变原始 ID、机器 JSON、查询和写入合同；CLI 终端输出与 ZIP 内 `content.md` 的 Markdown 导出格式分别遵守各自合同。新 Skill 继承共享展示规则。
- `HUMAN_ATTESTED_RESOLVE`：当前消息明确确认已解决且目标唯一，即人工结论与对应 Bug 的 R2 授权；最小 bug view → active 时一次 fixed resolve → 显式 bug view 回读。不读取业务仓库/源码/提交/测试/diff/附件/patch，不运行 select/snapshot/compare，不套用普通证据门槛。
- 人工确认默认显式 `--resolved-build trunk`，用户明确指定其它值时覆盖；负责人按“用户显式指定 assignee > Bug creator account > BLOCKED”确定，显式人员需由完整真实用户数据唯一解析，未指定时使用当前 Bug 的创建人 account，兼容 openedByAccount/openedBy.account；`openedBy` 字符串须经完整真实用户目录做区分大小写的 account 精确校验，不按姓名或大小写回退匹配；缺失、重名、冲突或数据不完整时停止，不回退、不猜测。resolve 必须显式传 `--assignee <target-account>`，回读同时验证 `status=resolved` 且 `assignedTo=target_account`；默认不传 resolved-date，自动生成 `[CODEX-HUMAN-ATTESTED-RESOLUTION]` 备注，不伪造代码或测试事实。resolved/closed 不重复写；当前消息明确列出的多个 Bug 按输入顺序去重并严格串行；真实阻塞停止，`UNKNOWN_WRITE_RESULT` 停止整个队列、只读回读且绝不重试。仅在真实阻塞时提问，不自动 close 或切换 endpoint。
- “帮我解决/修复”与不确定表达不触发人工确认；人工确认是 Agent 指令分支，没有新增 Python lifecycle 编排器，不改变 120 endpoint 或只读 facade。
- R3 delete 仍要求用户明确删除意图与 `--yes`；写请求网络失败不自动重试，未知结果使用 `UNKNOWN_WRITE_RESULT`。
- project scope Token 允许短期缓存到 `.tmp/zentao/auth/`；user scope 使用
  `~/.zentao-ai-assistant/cache/auth/`；不写回配置文件，不保存密码。明确 401
  会清理缓存并重新登录一次。
- project scope 的聚合/资源临时数据位于 `.tmp/zentao/<skill>/` 与
  `.tmp/zentao-resources/`；`zentao-batch-export` 的 run/staging/ZIP 位于 `.tmp/zentao/zentao-batch-export/`；user scope 位于
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
