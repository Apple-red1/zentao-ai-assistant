# 测试项目上下文合同

测试项目配置是本机 user-scope 长期配置，独立于 `.env`、Token cache、团队名单和临时数据：

```text
~/.zentao-ai-assistant/testing-projects/<sha256(normalized-base-url+account)>.json
```

测试团队另存于 `~/.zentao-ai-assistant/testing-teams/<identity-sha256>.json`；本文件中的
Project/Module 上下文不承载开发/个人团队或测试团队成员，更新项目上下文不会隐式改动任一
团队配置域。

配置根包含 `schema_version=1`、匹配的 `owner`、`projects` 和 `current`。每个项目保存
可为空的 `project_id`、`product_id`、`default_affected_build` 和 `modules`；模块保存 `module_id`、
`frontend_account`、`backend_account`。项目和模块别名大小写冲突时拒绝写入。

Project ID 已提供时，项目/Product/Build/用户校验使用基础 Skill public facade 的完整只读分页；
未提供 Project ID 时跳过项目候选和 Project/Product 关联校验。当前基础官方
 catalog 没有独立 Module list/view endpoint，因此模块配置只在 Product 详情明确返回
模块集合时标记 `verification.module=verified`；否则保留 `unverified` 并在输出中标记
不完整，不能把一个未经证明的数字写成已确认归属。Project/Product 详情缺少关联字段时
同样使用显式不完整标记；没有 Project ID 时该关联为 `not_applicable`。

所有本地更新都经过 identity-scoped JSON store：目录 `0700`、文件 `0600`、symlink 拒绝、
锁目录防并发覆盖、临时文件 flush/fsync 后原子替换。损坏、身份冲突、schema 不匹配或
超限文件均阻止覆盖旧配置。
