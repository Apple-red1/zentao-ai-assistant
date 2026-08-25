
# ZenTao API v2 能力目录

`endpoints.json` 是 2026-08-25 官方 API v2 调研快照的机器可读覆盖索引，当前固定为 20 个资源、120 个 endpoint。它用于审计和测试集合一致性，不参与运行时 HTTP 动态路由。

运行时参数合同以 `python skills/zentao/scripts/zentao.py <resource> <action> --help` 为准。真实 ZenTao 21.7.8 的兼容状态与官方能力覆盖分离：`not_observed` 表示尚未实测，`observed` 表示已在目标实例验证，`unsupported` 表示官方文档存在但目标实例明确未提供该能力。
