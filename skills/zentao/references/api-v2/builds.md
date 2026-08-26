# build · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `build.create` | `POST` `/api.php/v2/builds` | `build create` | R1 | 创建版本/构建 |
| `build.edit` | `PUT` `/api.php/v2/builds/{buildID}` | `build edit` | R1 | 修改版本 |
| `build.list_project` | `GET` `/api.php/v2/projects/{projectID}/builds` | `build list --project <id>` | R0 | 获取项目版本列表 |
| `build.list_execution` | `GET` `/api.php/v2/executions/{executionID}/builds` | `build list --execution <id>` | R0 | 获取执行版本列表 |
| `build.delete` | `DELETE` `/api.php/v2/builds/{buildID}` | `build delete` | R3 | 删除版本 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
