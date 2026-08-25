# 排错指南

先运行：

```bash
python skills/zentao/scripts/zentao.py doctor --json
```

| 错误码 | 含义 | 处理 |
|---|---|---|
| `CONFIG_ERROR` | `.env`/环境变量缺失或 URL 无效 | 对照 `.env.example` 检查三项连接配置。 |
| `USAGE_ERROR` | 参数、scope、枚举或删除确认不符合 CLI 合同 | 执行对应 `<resource> <action> --help`。 |
| `API_ERROR` | ZenTao 明确返回 HTTP/业务失败 | 根据 `details.status` 与最小必要响应信息检查权限、ID 和字段。 |
| `NETWORK_ERROR` | 请求确定未送达或 GET 重试耗尽 | 检查地址、DNS、TLS、网络和反向代理。 |
| `MALFORMED_RESPONSE` | API 返回无法解析的 JSON | 记录目标实例版本和 endpoint，作为兼容性差异处理。 |
| `UNKNOWN_WRITE_RESULT` | 写请求可能已经执行但响应不可确认 | 不要直接重放；先显式使用对应 view/list 读取当前状态，再决定后续动作。 |

自动化测试问题请运行：

```bash
python skills/zentao/tests/run_all.py
```

覆盖摘要任一 surface 低于 120/120 都应视为失败。
