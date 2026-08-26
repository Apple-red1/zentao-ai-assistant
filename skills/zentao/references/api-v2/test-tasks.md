# test-task · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `test-task.create` | `POST` `/api.php/v2/testtasks` | `test-task create` | R1 | 创建测试单 |
| `test-task.edit` | `PUT` `/api.php/v2/testtasks/{testtaskID}` | `test-task edit` | R1 | 修改测试单 |
| `test-task.list_product` | `GET` `/api.php/v2/products/{productID}/testtasks` | `test-task list --product <id>` | R0 | 获取产品测试单列表 |
| `test-task.list_project` | `GET` `/api.php/v2/projects/{projectID}/testtasks` | `test-task list --project <id>` | R0 | 获取项目测试单列表 |
| `test-task.list_execution` | `GET` `/api.php/v2/executions/{executionID}/testtasks` | `test-task list --execution <id>` | R0 | 获取执行测试单列表 |
| `test-task.delete` | `DELETE` `/api.php/v2/testtasks/{testtaskID}` | `test-task delete` | R3 | 删除测试单 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
