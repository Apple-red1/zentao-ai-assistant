# execution · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `execution.create` | `POST` `/api.php/v2/executions` | `execution create` | R1 | 创建执行 |
| `execution.edit` | `PUT` `/api.php/v2/executions/{executionID}` | `execution edit` | R1 | 修改执行 |
| `execution.list` | `GET` `/api.php/v2/executions` | `execution list` | R0 | 获取执行列表 |
| `execution.list_project` | `GET` `/api.php/v2/projects/{projectID}/executions` | `execution list --project <id>` | R0 | 获取项目的执行列表 |
| `execution.view` | `GET` `/api.php/v2/executions/{executionID}` | `execution view` | R0 | 获取执行详情 |
| `execution.delete` | `DELETE` `/api.php/v2/executions/{executionID}` | `execution delete` | R3 | 删除执行 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
