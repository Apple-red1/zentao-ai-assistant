
# Changelog

## Unreleased

- 主实现迁移为单一 `skills/zentao/` Skill。
- 移除 MCP Server、独立 Python 包/系统 CLI 与第三方运行时依赖。
- 建立 ZenTao API v2 20 资源 / 120 endpoint 的显式 Internal/CLI/Fake/Test 覆盖。
- 增加 R0-R3 风险分级、DELETE `--yes`、GET 有限重试和 `UNKNOWN_WRITE_RESULT` 语义。
