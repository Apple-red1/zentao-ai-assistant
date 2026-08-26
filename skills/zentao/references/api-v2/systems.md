# system · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `system.create` | `POST` `/api.php/v2/systems` | `system create` | R1 | 创建应用 |
| `system.edit` | `PUT` `/api.php/v2/systems/{systemID}` | `system edit` | R1 | 修改应用 |
| `system.list_product` | `GET` `/api.php/v2/products/{productID}/systems` | `system list --product <id>` | R0 | 获取产品应用列表 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
