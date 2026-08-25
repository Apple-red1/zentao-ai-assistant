# task · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `task.create` | `POST` `/api.php/v2/tasks` | `task create` | R1 | 创建任务 |
| `task.edit` | `PUT` `/api.php/v2/tasks/{taskID}` | `task edit` | R1 | 修改任务 |
| `task.list_execution` | `GET` `/api.php/v2/executions/{executionID}/tasks` | `task list --execution <id>` | R0 | 获取执行任务列表 |
| `task.view` | `GET` `/api.php/v2/tasks/{taskID}` | `task view` | R0 | 获取任务详情 |
| `task.start` | `PUT` `/api.php/v2/tasks/{taskID}/start` | `task start` | R2 | 启动任务 |
| `task.finish` | `PUT` `/api.php/v2/tasks/{taskID}/finish` | `task finish` | R2 | 完成任务 |
| `task.close` | `PUT` `/api.php/v2/tasks/{taskID}/close` | `task close` | R2 | 关闭任务 |
| `task.activate` | `PUT` `/api.php/v2/tasks/{taskID}/activate` | `task activate` | R2 | 激活任务 |
| `task.delete` | `DELETE` `/api.php/v2/tasks/{taskID}` | `task delete` | R3 | 删除任务 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
