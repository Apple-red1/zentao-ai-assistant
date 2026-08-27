# zentao-ai-assistant

当前行为与开发事实入口：[`docs/current-contract.md`](docs/current-contract.md)。

本仓库提供一组供 AI 使用的 ZenTao 项目管理 Skills：

- `zentao`：ZenTao API v2 原子读取/写入和附件资源能力；
- `zentao-statistics`：确定性统计、聚合和范围对比；
- `zentao-personal`：个人待办、风险、工作列表和摘要；
- `zentao-project-management`：Project / Execution 的进度事实、风险和工作量分析；
- `zentao-bug-resolver`：证据驱动的 Bug 只读 `select` / `snapshot` / `compare` 与 Agent 编排，以及明确人工确认后的受控回写。

运行时只依赖 Python 3.11+ 标准库，不依赖 MCP 或第三方 Python 包。

## 配置

复制 `.env.example` 为 `.env`，填写 `ZENTAO_BASE_URL / ZENTAO_ACCOUNT / ZENTAO_PASSWORD`。Token 不写回 `.env`，允许短期缓存在 Git ignored 的 `.tmp/zentao/auth/`。

## API Skill

```bash
python skills/zentao/scripts/zentao.py doctor --json
python skills/zentao/scripts/zentao.py bug list --product 1 --json
python skills/zentao/scripts/zentao.py resource fetch --object-type bug --object-id 123 --json
```

删除属于 R3，必须有明确删除意图并传 `--yes`。

## 高层 Skill 示例

```bash
python skills/zentao-statistics/scripts/zentao_statistics.py summary bug --product 1 --json
python skills/zentao-personal/scripts/zentao_personal.py overview --json
python skills/zentao-project-management/scripts/zentao_project_management.py health --project 12 --json
```

Bug 证据驱动流程的确定性脚本入口为：

```bash
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py select --product 1 --json
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py snapshot --bug-id 123 --json
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py compare --bug-id 123 --baseline-file <snapshot.json> --json
```

`zentao-bug-resolver` 脚本只通过 `zentao_skill.public` 只读 facade 读取 ZenTao，并由 Agent 在普通流程编排业务仓库证据、最小修改、验证和写前复查；它不是新的 API endpoint，不改变 `zentao` 的 120 endpoint 口径。普通流程的 `pending_queue` 不会自动继续；`complete=false`、`partial_failures`、`unsupported_filters` 或 `unavailable_fields` 必须保留并如实说明。需要 R2 生命周期写入时，必须在当前用户明确授权且对应分支门槛满足后回到基础 `zentao` CLI，resolver 脚本和 facade 不执行写入。

普通流程授权分为 `ANALYZE_ONLY`、`LOCAL_FIX_ALLOWED` 和 `RESOLVE_R2_ALLOWED`；结论分为
`SOLVABLE`、`UNCLEAR`、`NO_CODE_EVIDENCE`、`BLOCKED`。一次任务只处理当前 Bug，
pending 项不继承授权；模糊的“处理 Bug”最多允许本地修复，不等于 R2。只有
`SOLVABLE` 且证据、验证、diff 和写前 compare 均通过时，Agent 才能执行一次
`bug resolve` 并回读；`UNCLEAR`/`NO_CODE_EVIDENCE` 不修改业务代码。

用户明确说“3641 已解决”或目标唯一的“把刚才那个 Bug 标记已解决”时，进入
`HUMAN_ATTESTED_RESOLVE`：当前消息即人工结论和该 Bug 的 R2 授权。只做最小
`bug view`，active 时一次 `bug resolve --resolution fixed --resolved-build trunk`
并附自动生成的 `[CODEX-HUMAN-ATTESTED-RESOLUTION]` 备注，随后显式回读。
用户明确指定其它解决版本时覆盖 `trunk`；默认不传 assignee/resolved-date，不提前追问。
此分支不检查业务源码、提交、测试、diff、附件或 patch，不运行 select/snapshot/compare。
已 resolved/closed 不重复写；当前消息列出的多个已解决 Bug 严格串行，真实阻塞即停止；
`UNKNOWN_WRITE_RESULT` 停止整个队列、绝不重试，只读回读。不自动 close/activate/delete。
“帮我解决/修复 Bug”“修复后标记已解决”“应该好了”不会直接触发人工确认写入。

详细自然语言边界见各 Skill 的 `SKILL.md`。

## 测试

```bash
python tests/run_all.py
```

`zentao` API 专项仍维持 20 个资源、120 个官方 API v2 endpoint 的完整覆盖门槛；高层 Skill 的场景测试单独统计，不能把 API `120/120` 解释为整个项目的用户场景覆盖率。

高层 Skill 测试使用标准库桩和本地 FakeZenTao，Real API calls: 0；真实 ZenTao 兼容性不由这些测试冒充证明。
