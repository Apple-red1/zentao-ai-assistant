# requirement · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `requirement.create` | `POST` `/api.php/v2/requirements` | `requirement create` | R1 | 创建用户需求 |
| `requirement.edit` | `PUT` `/api.php/v2/requirements/{storyID}` | `requirement edit` | R1 | 修改用户需求 |
| `requirement.change` | `PUT` `/api.php/v2/requirements/{storyID}/change` | `requirement change` | R1 | 变更用户需求 |
| `requirement.list_product` | `GET` `/api.php/v2/products/{productID}/requirements` | `requirement list --product <id>` | R0 | 获取产品用户需求列表 |
| `requirement.view` | `GET` `/api.php/v2/requirements/{storyID}` | `requirement view` | R0 | 获取用户需求详情 |
| `requirement.close` | `PUT` `/api.php/v2/requirements/{storyID}/close` | `requirement close` | R2 | 关闭用户需求 |
| `requirement.activate` | `PUT` `/api.php/v2/requirements/{storyID}/activate` | `requirement activate` | R2 | 激活用户需求 |
| `requirement.delete` | `DELETE` `/api.php/v2/requirements/{storyID}` | `requirement delete` | R3 | 删除用户需求 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
