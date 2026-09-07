# Changelog

## 1.13.0

- 执行 Issue #66：为 `zentao-testing` 增加独立测试团队配置、全局默认/项目覆盖、显式个人团队导入和隔离失败语义，避免设置测试团队覆盖开发/个人团队。

## 1.12.0

- 执行 #63：统一 Bug `steps` 的真实换行合同，支持 UTF-8 文件和显式 JSON 单次解码，归一实际
  CRLF/CR 但保留字面量 `\\n`，并补充 create/edit 的 Fake/E2E 回归。
- 执行 #64：新增个人 `overview/worklist/brief --markdown` 的确定性 Bug 表格，并与测试端
  `my-bugs --markdown` 共用固定列、链接、占位和完整性呈现；保持个人 `--json` 合同不变。

## 1.11.0

- 执行 #62：新增 `zentao-testing` 测试端 Bug 工作台，提供身份隔离的测试项目/模块配置、
  负责人解析、本人未关闭 Bug 聚合和测试端操作边界。
- 测试项目的 Project ID 改为可选；缺失时不强求 Project/Product 关联，`my-bugs` 按 Product 范围读取。
- 共享本地 JSON 存储统一提供锁、权限、符号链接、schema/owner/大小校验和原子写入；
  active Bug 独立指派保留真实 ZenTao 21.7.8 环境门槛，当前为 `INCONCLUSIVE/ENVIRONMENT_BLOCKER`。

## 1.10.0

- 执行 #60：兼容 ZenTao Bug create/edit 表单中 `uid` 为 `type="text"` 的真实形态；仅按
  `uid` 字段白名单解析，保留 hidden 兼容，并对缺失、空值和冲突值继续 fail-closed。

## 1.9.0

- 修复 #59 的实际编排缺口：聊天附件明确要求进入 Bug 描述/重现步骤时，强制路由到
  `steps-inline-image`，禁止降级为评论备注；补充本地附件路径缺失和插件缓存重载边界。

## 1.8.0

- 执行 #59：Bug `create/edit` 新增 `--steps-inline-image`，通过固定同源页面表单把本地图片直接嵌入 `steps`，并补充 fail-closed、回读归属校验和 Fake/E2E 覆盖。

## Unreleased

- 插件升级到 `1.7.0`。修复 #58：团队 active Bug 继续按 `assignedTo` 归属，resolved Bug 改按 `resolvedBy` 归入解决人的“待测试验证”，保留当前测试负责人展示，并对归属/展示字段异常 fail-visible。
- 插件升级到 `1.6.0`。实现 #48：`zentao-personal` 支持用户默认团队名单维护、团队 Bug 与团队日报；按实例/账号隔离持久化，完整分页、active/resolved 分区、成员四列表格和失败完整性共用同一数据链路。
- facade 增加不含秘密的连接身份和可选部分页保留，维持默认异常行为及 120 endpoint 只读边界。
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
