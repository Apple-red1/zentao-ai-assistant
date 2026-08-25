# ZenTao 21.7.8 兼容性状态

官方 API v2 合同与目标实例兼容性是两个独立维度。本文件记录 2026-08-25 在全新 ZenTao 21.7.8 实例上的真实验收结果；凭证仍只从本地 `.env` 读取，不写入仓库。

## 已验证

- 本地自动化全量测试：86 tests passed；Catalog、Internal、CLI、Fake、Contract、CLI E2E 均为 120/120；独立 Official snapshot 120/120，Specific sources 11/120，真实 API 调用计数为 0。
- 真实只读 endpoint-level evidence：5 个 endpoint ID 通过（`token.login`、`product.list`、`project.list`、`bug.list_product`、`bug.list_project`），具体 case 记录在 compatibility evidence 文件中；不再使用无法追溯的“44/44”口径。
- 真实对象资源获取：`resource fetch --object-type product --object-id 2` 返回空资源成功；临时 Bug 的富文本保留同源 `/theme/default/images/main/logo.png`，`resource fetch --object-type bug --object-id 3` 成功流式下载 2,067 字节 PNG，落盘文件与直接服务器响应 SHA-256 一致；临时对象已清理。
- 真实写入和状态流：项目集、产品、项目、执行、构建、应用、需求、用户需求、业务需求、任务、测试用例、测试单、Bug、用户的创建/编辑，以及需求/业务需求关闭激活、任务开始完成关闭激活、Bug 解决关闭激活均已成功。
- 本轮创建的数据先用于后续真实编辑与列表回读；已清理可确认且不影响依赖的测试叶子对象，承载测试的产品/项目层级仍保留；系统没有 `system.delete` 端点。

## 已同步的 21.7.8 差异

`endpoints.json` 的 compatibility 状态由 `skills/zentao/references/compatibility/zentao-21.7.8.json`
逐条校验。当前 120 个 endpoint 的机器统计为：

```text
observed      = 24
unsupported   = 16
not_observed  = 80
```

只有有真实 evidence 的条目才标为 `observed`；没有 endpoint-level evidence 的条目
保持 `not_observed`，不会因为历史“44/44”叙述而批量升级。已记录的兼容差异包括：

- `test-case.create`、`test-task.create`：服务端要求同时接收 `productID` 和兼容字段 `product`。
- `user.create`：服务端要求 `visions`，CLI 默认发送 `rnd`。
- `requirement.change`：服务端实际要求 `reviewer`；`user.edit`：服务端实际要求 `account`。
- `requirement.edit`、`epic.edit`：真实实例接受分类字符串，CLI 同时兼容字符串和数字 ID。
- `product-plan.create`、`product-plan.edit`：真实实例创建/编辑时分别要求兼容字段 `product`、`productID`，编辑还必须保留当前 `status`；`branchID` 与 `branch` 同时发送。
- `release.create`、`release.edit`：`status=normal` 时要求 `releasedDate`；编辑还必须同时保留 `productID` 与 `product`。

## 当前实例限制

- 反馈与工单模块：目标实例对创建、列表、详情及生命周期请求返回空响应（CLI 旧逻辑会渲染为 `status: success`）；产品配置探针返回 `Feedback does not exist.`，确认当前 21.7.8 未启用对应模块。代码现会把缺少对象字段的响应报告为 `API_ERROR`，而不是假成功。
- 文件模块：在真实任务上上传后返回空响应，任务详情仍为 `files: []`；编辑同样返回空响应，未猜测附件 ID 执行删除。官方上传文档将该接口标注为 v22.0 及以上能力。

发布前自动化门槛见 [release-checklist.md](../release-checklist.md)：完整测试必须在 Fake 环境达到 120/120，且真实 API 调用计数为 0。官方合同快照与 21.7.8 观察分别见 `skills/zentao/references/api-v2/official-contract.json` 和 `skills/zentao/references/compatibility/zentao-21.7.8.json`；文档统计必须与机器 evidence contract 一致。

## 对象关联资源获取：已完成真实 21.7.8 复验

本次新增 `resource fetch` 后，本地 Fake 已覆盖附件区 + 富文本资源发现、HTTP 二进制流式落盘、data URI、同名不覆盖、部分失败、同源重定向和跨源重定向拦截。官方 120 endpoint 覆盖集合保持不变。

本次使用项目 `.env` 连接真实实例完成对象详情读取和同源富文本图片下载。已观察到：

- 富文本中的同源绝对/根相对图片 URL 可被发现并下载；资源 GET 携带 API Token 即可成功；
- 返回的 `Content-Type: image/png` 和二进制内容均按流式方式保存，未发生内容改写；
- 21.7.8 实例的 `file upload` 写入端点返回空响应，Bug 详情的 `files` 仍为空；因此本次未把附件区下载标记为真实 `verified`，附件字段兼容性仍待支持该端点的实例复验；
- 本次未发现真实资源重定向链，重定向和跨源拦截仍由 Fake E2E 覆盖。

上述真实观察不改变官方 120 endpoint catalog；若后续实例提供附件元数据或重定向链，应记录为新的 21.7.8 `observed` 兼容事实后再扩展证据。
