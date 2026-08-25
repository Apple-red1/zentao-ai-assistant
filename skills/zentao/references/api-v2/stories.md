# story · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `story.create` | `POST` `/api.php/v2/stories` | `story create` | R1 | 创建研发需求 |
| `story.edit` | `PUT` `/api.php/v2/stories/{storyID}` | `story edit` | R1 | 修改研发需求 |
| `story.change` | `PUT` `/api.php/v2/stories/{storyID}/change` | `story change` | R1 | 变更研发需求 |
| `story.list_product` | `GET` `/api.php/v2/products/{productID}/stories` | `story list --product <id>` | R0 | 获取产品研发需求列表 |
| `story.list_project` | `GET` `/api.php/v2/projects/{projectID}/stories` | `story list --project <id>` | R0 | 获取项目研发需求列表 |
| `story.list_execution` | `GET` `/api.php/v2/executions/{executionID}/stories` | `story list --execution <id>` | R0 | 获取执行研发需求列表 |
| `story.view` | `GET` `/api.php/v2/stories/{storyID}` | `story view` | R0 | 获取研发需求详情 |
| `story.close` | `PUT` `/api.php/v2/stories/{storyID}/close` | `story close` | R2 | 关闭研发需求 |
| `story.activate` | `PUT` `/api.php/v2/stories/{storyID}/activate` | `story activate` | R2 | 激活研发需求 |
| `story.delete` | `DELETE` `/api.php/v2/stories/{storyID}` | `story delete` | R3 | 删除研发需求 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
