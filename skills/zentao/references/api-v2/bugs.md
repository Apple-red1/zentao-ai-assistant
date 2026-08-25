# bug · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `bug.create` | `POST` `/api.php/v2/bugs` | `bug create` | R1 | 创建 Bug |
| `bug.edit` | `PUT` `/api.php/v2/bugs/{bugID}` | `bug edit` | R1 | 修改 Bug |
| `bug.list_product` | `GET` `/api.php/v2/products/{productID}/bugs` | `bug list --product <id>` | R0 | 获取产品 Bug 列表 |
| `bug.list_project` | `GET` `/api.php/v2/projects/{projectID}/bugs` | `bug list --project <id>` | R0 | 获取项目 Bug 列表 |
| `bug.list_execution` | `GET` `/api.php/v2/executions/{executionID}/bugs` | `bug list --execution <id>` | R0 | 获取执行 Bug 列表 |
| `bug.view` | `GET` `/api.php/v2/bugs/{bugID}` | `bug view` | R0 | 获取 Bug 详情 |
| `bug.resolve` | `PUT` `/api.php/v2/bugs/{bugID}/resolve` | `bug resolve` | R2 | 解决 Bug |
| `bug.close` | `PUT` `/api.php/v2/bugs/{bugID}/close` | `bug close` | R2 | 关闭 Bug |
| `bug.activate` | `PUT` `/api.php/v2/bugs/{bugID}/activate` | `bug activate` | R2 | 激活 Bug |
| `bug.delete` | `DELETE` `/api.php/v2/bugs/{bugID}` | `bug delete` | R3 | 删除 Bug |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。

Bug 列表的官方 `browseType` 范围按 scope 区分：产品支持
`all | unclosed | assignedtome | openedbyme | assignedbyme`；项目和执行支持
`all | unresolved`。CLI 的 `assigned-to-me`、`opened-by-me`、`assigned-by-me`
会映射为对应 API 值。详见独立官方合同快照和 #9 的 API v2 deep-link 证据。
