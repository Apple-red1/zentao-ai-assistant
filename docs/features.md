# 功能概览

当前产品是面向 AI 的 ZenTao 项目管理 Skill 集合：一个基础 API Skill 加五个
高层 Skill。Plugin 与 Clone 共用仓库根目录的同一份 `skills/`，`_shared` 不是
公开 Skill。

## 支持矩阵

| Surface | v1 状态 |
|---|---|
| Clone + Codex | supported |
| Clone + Claude Code | supported via `CLAUDE.md` |
| Clone + Gemini CLI | supported via `GEMINI.md` |
| Claude Code Plugin | v1 formal support；发布前必须通过 T10 真实宿主 gate |
| Codex Plugin | v1 formal support；发布前必须通过 T10 真实宿主 gate |
| Gemini Plugin/Extension | not included in v1 |
| Cursor/Copilot/VS Code Plugin | standards-compatible direction / independently unverified |

上表的 Plugin formal support 是本版本交付目标；静态 manifest、单元测试或文档
不能替代 T10 的真实 validate/load/install/discovery/cache 验收。

## `zentao`

基础 API Skill 覆盖 20 个资源、120 个 ZenTao API v2 endpoint；Token 是内部认证能力，其余官方资源通过统一 `<resource> <action> [scope] [parameters]` CLI 暴露。另提供对象关联资源获取和仓库内部 programmatic public facade。

## `zentao-statistics`

确定性统计、聚合、分页、去重和同类范围比较。第一版支持 Bug、Task、Story、Requirement、Test Case、Test Task、Ticket、Feedback。

## `zentao-personal`

当前或指定用户的个人工作概览、待办清单、Severity 1 / P1 Bug、逾期任务及日报/周报事实素材。

## `zentao-project-management`

Project / Execution 的资源概览、风险信号和开放事项工作量分布。默认不发明数值健康分或人员绩效结论。

## `zentao-batch-export`

按显式 `type:id` 批量导出多个 ZenTao 对象，首版覆盖当前 13 种同时具备 `view + resource fetch` 的 canonical 类型。每个对象的 `content.md` 保存完整 `view --json` 响应，附件和富文本资源进入独立 `resources/`，根 `manifest.json` 只记录路径、完整性与失败清单。单项失败继续导出；最终 ZIP 位于当前 runtime scope 的 `zentao/zentao-batch-export/<run-id>/` 并动态命名。

## `zentao-bug-resolver`

普通流程面向单个当前 Bug。确定性脚本提供只读 `select`、`snapshot`、`compare`，Agent 再据此编排 ZenTao/业务仓库证据、最小修改、真实验证和写前复查。

`pending_queue` 只保留待处理项，不自动继续；`complete=false`、`partial_failures`、`unsupported_filters` 和 `unavailable_fields` 必须作为证据边界保留。该 Skill 的脚本/组合能力不是 API endpoint，不计入基础 `zentao` 的 120 个 ZenTao API v2 endpoint；程序化 facade 只读，需要 R2 生命周期写入时必须回到基础 `zentao` CLI，并取得当前用户明确授权。

高层 Skill 测试使用标准库桩或本地 FakeZenTao，不访问真实 ZenTao（`Real API calls: 0`）。

Plugin 配置使用 `setup --scope user`，连接配置位于
`~/.zentao-ai-assistant/config.env`，Token/cache/tmp 不写入 Claude/Codex
Plugin cache。Clone 默认使用 project scope 的仓库 `.env` / `.tmp`；完整步骤见
[`docs/installation.md`](installation.md) 和 [`docs/configuration.md`](configuration.md)。

普通流程授权采用 `ANALYZE_ONLY`、`LOCAL_FIX_ALLOWED`、`RESOLVE_R2_ALLOWED`，证据结论采用
`SOLVABLE`、`UNCLEAR`、`NO_CODE_EVIDENCE`、`BLOCKED`。一次任务只处理当前 Bug，
pending 项不继承授权；模糊“处理 Bug”不产生 R2。只有满足完整证据、验证、diff 和
写前比较门槛时，Agent 才能回到基础 `zentao` CLI 执行一次 `bug resolve` 并回读；
`UNCLEAR`/`NO_CODE_EVIDENCE` 不修改代码。

`HUMAN_ATTESTED_RESOLVE` 是独立的人工确认分支：用户明确说已解决且目标唯一时，
当前消息即该 Bug 的人工结论与 R2 授权。只做最小 bug view，active 时一次 fixed resolve，
随后显式回读；resolved/closed 不重复写。默认 `--resolved-build trunk`，用户明确指定时覆盖，
负责人按“用户显式指定 assignee > Bug creator account > BLOCKED”确定，显式人员需由完整真实用户数据唯一解析，未指定时使用当前 Bug 的创建人 account，兼容 openedByAccount/openedBy.account；`openedBy` 字符串须经完整真实用户目录做区分大小写的 account 精确校验，不按姓名或大小写回退匹配；缺失、重名、冲突或数据不完整时停止，不回退、不猜测。resolve 必须显式传 `--assignee <target-account>`，回读同时验证 `status=resolved` 且 `assignedTo=target_account`；默认不传 resolved-date，自动生成 HUMAN-ATTESTED 备注。不审计业务代码、提交、测试、
diff、附件或 patch，不运行 select/snapshot/compare。当前消息明确列出的多个 Bug 严格串行，
真实阻塞或 UNKNOWN_WRITE_RESULT 停止整个队列；未知写入只读回读、绝不重试，不自动 close。
普通“修复 Bug”或“应该好了”不触发该分支。
