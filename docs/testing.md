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

后续增加场景时优先覆盖多页、空集、部分失败、重复数据、日期边界和真实用户表达。

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

## 对象 Web URL 输出规则（Issue #45）

本轮修复的是 Agent 指令，未新增页面生成器或验证器。测试范围必须分别说明：

- `test_current_contract.py` 静态检查六个 Skill、Clone 入口、Bug reference/workflow
  均引用统一的[链接证据合同](../skills/zentao/references/web-urls.md)，并检查只有 ID、
  历史示例、query/rewrite、HTTP 200 登录页/首页/软 404、子路径、不可验证、用户模板
  八类场景的指令门槛。它不运行模型或网页识别器。
- `test_skill_scenarios.py` 通过本地 Fake 执行真实 `bug view` CLI：只有 ID 或富文本
  示例时不生成详情 URL；API 明确返回 URL/link 时保留路径、部署前缀及查询参数，
  不添加已验证声明，不发送页面探测请求。Fake URL 不是实际实例兼容性证据。
- 模型回答需按上述八类场景在宿主中人工验收：尤其是“给我五个 Bug 的 URL”后，
  在无证据或收到“链接不对”时是否停止猜测；HTTP 200 登录页不得被当作对象页。
  自动化通过不代表模型任意表达均通过，也不代表真实页面路由已验证。

专项命令（在 `skills/zentao` 目录执行）：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3 -m unittest -v tests.catalog.test_current_contract tests.scenarios.test_skill_scenarios
```

## Release gate 入口

发布前必须依次保留 L3/L4 的真实宿主证据，再完整执行：

```bash
python skills/zentao/tests/run_all.py
python tests/run_all.py
```

两条 runner 均须报告 `120/120`、`Real API calls: 0` 和 `Result: PASS`；Fake/自动化
不得连接真实 ZenTao。没有 L3/L4 证据时，不能把 release checklist 标为完成。
