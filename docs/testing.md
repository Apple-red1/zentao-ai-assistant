# 测试

全部测试仅使用 Python 标准库，默认不得连接真实 ZenTao。

## 验证层次

```text
L0 config/runtime-path unit
L1 plugin static contract
L2 repository/current contract + Fake/smoke
L3 Claude real host gate
L4 Codex real host gate
L5 full regression
```

L0-L2 只验证本地实现、manifest/目录合同和 loopback Fake；静态 JSON PASS 不等于
正式 Plugin 支持。L3/L4 必须由真实宿主完成 validate/load/install/discovery，
并检查宿主缓存副本仍能运行共享 `scripts/_shared`。Claude 或 Codex 客户端/安装
surface 不可用时，结果必须记录为 `BLOCKED_ENVIRONMENT`，不能降级成静态通过。

## 仓库级入口

```bash
python tests/run_all.py
```

该入口先执行 `zentao` API Skill 的完整门槛，再执行 `zentao-statistics`、`zentao-personal`、`zentao-project-management`、`zentao-bug-resolver`、`zentao-batch-export` 的专项单元/行为测试。

## API Skill

```bash
python skills/zentao/tests/run_all.py
```

继续验证 catalog、Internal、CLI、Skill routes、Fake、Contract、CLI E2E 精确 `120/120`，以及 official contract / 21.7.8 compatibility evidence。Fake 只证明本地合同，不证明真实 ZenTao 兼容性。

新增 Token cache / public facade 测试覆盖：

- cache scope、TTL、POSIX 权限和不保存密码；
- cached token 收到明确 401 后只刷新一次；
- programmatic `list_all()` 根据 pager 完整翻页；
- 不支持的 resource/scope 与写操作在调用业务 Service 前拒绝；重复页会标记 `PAGINATION_STALLED`，不能误报完整。

Runtime 测试还覆盖 project/user 的 config/cache/tmp 路径隔离、用户目录权限、
explicit config 选择和临时 HOME；不会读取真实 `.env` 或写入 Claude/Codex Plugin
cache。

## 高层 Skill

- `zentao-statistics`：去重、状态/负责人/优先级/严重程度、Task deadline、compare。
- `zentao-personal`：用户重名、个人过滤、严重 Bug、逾期 Task。
- `zentao-project-management`：事实型 health signals、无数值健康分、开放事项 workload。
- `zentao-bug-resolver`：只读 `select`、Bug snapshot、写前 `compare` 及证据完整性边界。
- `zentao-batch-export`：混合类型去重、完整字段 Markdown、资源归档、部分失败继续、动态 ZIP、runtime scope 与路径安全。

resolver 的多 Skill smoke 使用本地 FakeZenTao 服务器，由独立子进程实际运行 `select`、`snapshot`、`compare`；断言业务请求均为 GET、没有 `bug.resolve`，因此不代表真实 ZenTao 调用。全仓库和 API 专项结果中的 `Real API calls: 0` 仍是硬边界：测试只验证本地 Fake/桩合同，不验证真实环境兼容性。

批量导出还应覆盖 Markdown 字段格式化、富文本资源引用替换为 ZIP 相对路径、重复文件名、部分失败继续和失败详情保留。后续增加场景时优先覆盖多页、空集、部分失败、重复数据、日期边界和真实用户表达。

## Bug ID 聊天展示

统一合同位于 `skills/zentao/references/bug-display.md`，六个 `SKILL.md` 均直接引用。
Issue #46 r3 实施时用户确认：不包含 CLI 不带 `--json` 的终端输出和 ZIP 内
`content.md`；只改变聊天富文本，原始机器数据与业务流程保持不变。

当前源码展示出口清单（每个场景只在聊天实际出现 Bug ID 时加链接）：

| Skill / 场景 | 数据来源与必须保留的合同 | 聊天走查重点 |
|---|---|---|
| `zentao` 查询、链接、操作结果 | `cli/bugs/commands.py` 的原始结果；`cli/output.py` 与 `presenters/generic.py` 不改 | 正文 `Bug ID` 的编号可点击；不额外查询或改变写入结果 |
| `zentao-personal` 列表、概览、摘要 | `zentao_personal.py` 的 `build_worklist`、`build_personal_overview`；原始 `resource/id` | 表格编号可点击，原表头、顺序、其它列和数据边界不变 |
| `zentao-project-management` Project/Execution 风险与说明 | `zentao_project_management.py` 的 `build_health_report` / `risk_signals` | Bug 风险项加链接，混合 Task 等资源的 ID 不误链，保留部分失败 |
| `zentao-bug-resolver` 目标、候选、队列、状态回报 | `select_bugs` / `build_snapshot` / `compare_snapshots` 与 Agent 显式回读 | 编号链接不触发详情读取、队列继续、证据流程或生命周期写入 |
| `zentao-statistics` 统计解释 | `summarize_records` / `compare_summaries` 通常只含聚合；scope ID 不是 Bug ID | 纯数量不生成链接；从已有明细引用单个 Bug 时才加链接，不为此取明细 |
| `zentao-batch-export` 导出结果聊天说明 | `export_objects` 的输出与 manifest；`content.md` 的 Markdown 格式、资源相对路径、失败文件及 ZIP 内容遵守批量导出合同 | 聊天提到的成功/失败 Bug 编号可点击，完整性与失败事实不变 |

确定性回归入口：

```bash
python3 -B -m unittest discover -s tests -p 'test_web_url_route.py'
```

该测试运行真实 `cli.main` 入口，隔离配置并禁止网络、登录和浏览器，验证现有
单对象/数组 JSON 形态、整数 ID、重复/乱序批量映射、实例路径和非法 ID 错误。
它是基础能力回归，不是自然语言展示行为测试；原有生产 Python 不变，这些测试
在指令修改前也应通过，不能称作由新展示规则修复的 Red。

Agent 场景走查应分别提供上述六个 Skill 和虚构的已有结果，不提供预期回答。
检查表格、正文、摘要/候选项以及导出结果回复中的编号是否可点击、是否按 ID
关联 URL，并检查相同编号的 Task 不误链、纯统计不补明细、失败不猜 URL、
resolver 不继续处理或写入。记录实际输出和工具调用；文档关键词检查或手工
拼出的 Markdown 示例不能替代该走查。场景通过不代表任意模型/宿主都已验收。

## 人工确认分支

`HUMAN_ATTESTED_RESOLVE` 不新增 Python 写入编排器。测试分开验证以下范围：

- resolver 静态合同：明确完成表达与唯一目标、普通流程不误触发、跳过业务审计、单次 resolve/显式回读、resolved/closed 零写入、多 ID 严格串行、真实阻塞停止、未知写入不重试、脚本只读边界；UI prompt 不再强制先取 snapshot。
- 真实 CLI 示例：从 workflow 提取命令，在本地 FakeZenTao 上执行，验证 `fixed`、默认 `--resolved-build trunk`、明确版本覆盖、UTF-8 备注、默认不传 assignee/resolved-date，及权限/校验/未知写入的结果和显式回读。
- 自然语言路由与队列决策属于 Agent 指令，需要场景走查；静态断言或 CLI smoke 不能证明模型对任意表达都能正确编排，也不证明真实 ZenTao 兼容性。

专项入口：

```bash
python -m unittest discover -s skills/zentao-bug-resolver/tests -p 'test_*.py'
python -m unittest discover -s skills/zentao-batch-export/tests -p 'test_*.py'
python -m unittest discover -s tests -p 'test_multiskill_smoke.py'
```

全仓入口包含上述检查。所有自动化只访问本地 Fake/桩，Real API calls: 0；真实用户验收应另行记录。

## Release gate 入口

发布前必须依次保留 L3/L4 的真实宿主证据，再完整执行：

```bash
python skills/zentao/tests/run_all.py
python tests/run_all.py
```

两条 runner 均须报告 `120/120`、`Real API calls: 0` 和 `Result: PASS`；Fake/自动化
不得连接真实 ZenTao。没有 L3/L4 证据时，不能把 release checklist 标为完成。
