# ZenTao 21.7.8 兼容性状态

官方 API v2 合同与目标实例兼容性是两个独立维度。本文件记录 2026-08-25 在全新 ZenTao 21.7.8 实例上的真实验收结果；凭证仍只从本地 `.env` 读取，不写入仓库。

## 已验证

- 本地 Fake 全量测试：44 tests passed；Catalog、Internal、CLI、Fake、Contract、CLI E2E 均为 120/120，真实 API 调用计数为 0。
- 真实只读端点：44/44 通过，覆盖列表、详情、分页、排序、筛选和 token/doctor 流程。
- 真实写入和状态流：项目集、产品、项目、执行、构建、应用、需求、用户需求、业务需求、任务、测试用例、测试单、Bug、用户的创建/编辑，以及需求/业务需求关闭激活、任务开始完成关闭激活、Bug 解决关闭激活均已成功。
- 本轮创建的可确认对象已按依赖顺序清理；系统没有 `system.delete` 端点，产品删除后系统列表为空。

## 已同步的 21.7.8 差异

`endpoints.json` 已将对应端点标为 `observed`，并同步 Fake 合同与 CLI 样例：

- `test-case.create`、`test-task.create`：服务端要求同时接收 `productID` 和兼容字段 `product`。
- `user.create`：服务端要求 `visions`，CLI 默认发送 `rnd`。
- `requirement.change`：服务端实际要求 `reviewer`；`user.edit`：服务端实际要求 `account`。
- `requirement.edit`、`epic.edit`：真实实例接受分类字符串，CLI 同时兼容字符串和数字 ID。

## 当前实例限制

- `release.create` 按官方字段发送仍返回“应用版本号不能为空”，且发布列表为空；没有生成可确认的发布 ID。
- 产品计划、反馈、工单创建接口返回 `status: success` 但没有 ID；随后列表/详情没有对应对象，因此未继续编辑或删除未知 ID。
- 文件上传返回 `status: success` 但没有文件 ID，Bug 详情仍为 `files: []`；未猜测附件 ID 执行编辑/删除。官方文档将该上传接口标注为 v22.0 及以上能力。

发布前自动化门槛见 [release-checklist.md](../release-checklist.md)：完整测试必须在 Fake 环境达到 120/120，且真实 API 调用计数为 0。真实实例差异以本文件和 `endpoints.json` 的 `observed` 记录为准。
