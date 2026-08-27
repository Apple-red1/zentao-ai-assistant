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

该入口先执行 `zentao` API Skill 的完整门槛，再执行 `zentao-statistics`、`zentao-personal`、`zentao-project-management`、`zentao-bug-resolver` 的专项单元/行为测试。

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

resolver 的多 Skill smoke 使用本地 FakeZenTao 服务器，由独立子进程实际运行 `select`、`snapshot`、`compare`；断言业务请求均为 GET、没有 `bug.resolve`，因此不代表真实 ZenTao 调用。全仓库和 API 专项结果中的 `Real API calls: 0` 仍是硬边界：测试只验证本地 Fake/桩合同，不验证真实环境兼容性。

后续增加场景时优先覆盖多页、空集、部分失败、重复数据、日期边界和真实用户表达。

## Release gate 入口

发布前必须依次保留 L3/L4 的真实宿主证据，再完整执行：

```bash
python skills/zentao/tests/run_all.py
python tests/run_all.py
```

两条 runner 均须报告 `120/120`、`Real API calls: 0` 和 `Result: PASS`；Fake/自动化
不得连接真实 ZenTao。没有 L3/L4 证据时，不能把 release checklist 标为完成。
