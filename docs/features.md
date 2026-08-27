# 功能概览

当前产品是面向 AI 的 ZenTao 项目管理 Skill 集合：一个基础 API Skill 加四个
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

## `zentao-bug-resolver`

面向单个当前 Bug 的证据驱动流程。确定性脚本提供只读 `select`、`snapshot`、`compare`，Agent 再据此编排 ZenTao/业务仓库证据、最小修改、真实验证和写前复查。

`pending_queue` 只保留待处理项，不自动继续；`complete=false`、`partial_failures`、`unsupported_filters` 和 `unavailable_fields` 必须作为证据边界保留。该 Skill 的脚本/组合能力不是 API endpoint，不计入基础 `zentao` 的 120 个 ZenTao API v2 endpoint；程序化 facade 只读，需要 R2 生命周期写入时必须回到基础 `zentao` CLI，并取得当前用户明确授权。

高层 Skill 测试使用标准库桩或本地 FakeZenTao，不访问真实 ZenTao（`Real API calls: 0`）。

Plugin 配置使用 `setup --scope user`，连接配置位于
`~/.zentao-ai-assistant/config.env`，Token/cache/tmp 不写入 Claude/Codex
Plugin cache。Clone 默认使用 project scope 的仓库 `.env` / `.tmp`；完整步骤见
[`docs/installation.md`](installation.md) 和 [`docs/configuration.md`](configuration.md)。

授权采用 `ANALYZE_ONLY`、`LOCAL_FIX_ALLOWED`、`RESOLVE_R2_ALLOWED`，证据结论采用
`SOLVABLE`、`UNCLEAR`、`NO_CODE_EVIDENCE`、`BLOCKED`。一次任务只处理当前 Bug，
pending 项不继承授权；模糊“处理 Bug”不产生 R2。只有满足完整证据、验证、diff 和
写前比较门槛时，Agent 才能回到基础 `zentao` CLI 执行一次 `bug resolve` 并回读；
`UNCLEAR`/`NO_CODE_EVIDENCE` 不修改代码。
