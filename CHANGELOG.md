# Changelog

## Unreleased

- 合并版插件统一升级到 `1.5.0`；保留 Markdown 批量导出与旧式富文本图片下载修复。
- 修复 #47：人工确认解决 Bug 时，显式指定负责人优先；否则校验创建人账号，`openedBy` 字符串须经完整用户目录精确匹配，并在 resolve 后同时核对状态和负责人。
- 批量导出的对象详情改为可读 Markdown，并把已归档的富文本图片/文件引用改为 ZIP 内 `resources/` 相对路径。
- 兼容 ZenTao 富文本旧式图片 URL：受限将 `file/read` 转为 `file/download`，同时保留原始 `source` 并继续执行资源安全校验。
- 将仓库定位升级为面向 AI 的 ZenTao 项目管理多 Skill 集合。
- 新增 `zentao-statistics`、`zentao-personal`、`zentao-project-management`。
- 新增只读 `zentao_skill.public` programmatic facade、完整分页读取和分页停滞检测。
- 新增 `.tmp/zentao/auth/` 短期 Token cache，支持明确 401 后刷新。
- 新增 project/user RuntimePaths：user 配置、Token/cache/tmp 统一位于
  `~/.zentao-ai-assistant/`，并让高层临时材料与资源按 scope 隔离。
- 新增 portable `plugin.json`、Claude Plugin marketplace、Codex repo
  marketplace，以及不复制 Skill 的 Clone bridge 路由。
- 新增仓库级 `python tests/run_all.py` 测试入口。
