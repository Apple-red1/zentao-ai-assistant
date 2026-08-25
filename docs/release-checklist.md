# 发布检查清单

## 架构与安全

- [ ] 主实现只位于 `skills/zentao/`，不存在 MCP Server、独立 `src/zentao_ai/` 主实现或系统级 `zentao-ai` 产品入口。
- [ ] 运行时与测试只使用 Python 标准库。
- [ ] `.env.example` 只有三项连接模板，真实 `.env` 不进入 Git。
- [ ] CLI/Services 不直接使用 `urllib` 或拼接 `/api.php/v2`。
- [ ] Token 只存在进程内，输出对 password/token/Authorization/Cookie 类字段递归脱敏。
- [ ] 所有 R3 delete 在缺少 `--yes` 时不发送业务 HTTP。
- [ ] 写入网络不确定返回 `UNKNOWN_WRITE_RESULT`，不自动重试、不自动 GET。

## 全量覆盖

执行：

```bash
python skills/zentao/tests/run_all.py
```

必须同时得到：Catalog、Internal、CLI、Skill routes、Fake API、Contract tests、CLI E2E 均为 `120 / 120`，`Real API calls: 0`，最终 `Result: PASS`。

另外检查报告中的 `Official snapshot` 与 `Specific sources`。前者是 runtime
catalog 与独立官方快照的比对，后者只统计有 endpoint-specific 官方 deep link 的
条目；generic index URL 必须带明确的待核对说明，不能伪装成已逐项验证。

## 兼容性

自动化发布门槛使用完整本地 Fake ZenTao。真实 ZenTao 21.7.8 或其他版本的差异根据实际运行证据记录在独立的 `skills/zentao/references/compatibility/` evidence 文件中；必要时再同步 `endpoints.json` 的 compatibility 元数据，不用 Fake 结果冒充真实实例兼容性。
