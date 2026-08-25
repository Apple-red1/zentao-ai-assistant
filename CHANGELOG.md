# Changelog

## Unreleased

- 将仓库定位升级为面向 AI 的 ZenTao 项目管理多 Skill 集合。
- 新增 `zentao-statistics`、`zentao-personal`、`zentao-project-management`。
- 新增只读 `zentao_skill.public` programmatic facade、完整分页读取和分页停滞检测。
- 新增 `.tmp/zentao/auth/` 短期 Token cache，支持明确 401 后刷新。
- 新增仓库级 `python tests/run_all.py` 测试入口。
