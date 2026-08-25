# epic · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `epic.create` | `POST` `/api.php/v2/epics` | `epic create` | R1 | 创建业务需求 |
| `epic.edit` | `PUT` `/api.php/v2/epics/{storyID}` | `epic edit` | R1 | 修改业务需求 |
| `epic.change` | `PUT` `/api.php/v2/epics/{storyID}/change` | `epic change` | R1 | 变更业务需求 |
| `epic.list_product` | `GET` `/api.php/v2/products/{productID}/epics` | `epic list --product <id>` | R0 | 获取产品业务需求列表 |
| `epic.view` | `GET` `/api.php/v2/epics/{storyID}` | `epic view` | R0 | 获取业务需求详情 |
| `epic.close` | `PUT` `/api.php/v2/epics/{storyID}/close` | `epic close` | R2 | 关闭业务需求 |
| `epic.activate` | `PUT` `/api.php/v2/epics/{storyID}/activate` | `epic activate` | R2 | 激活业务需求 |
| `epic.delete` | `DELETE` `/api.php/v2/epics/{storyID}` | `epic delete` | R3 | 删除业务需求 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
