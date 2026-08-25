# project · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `project.create` | `POST` `/api.php/v2/projects` | `project create` | R1 | 创建项目 |
| `project.edit` | `PUT` `/api.php/v2/projects/{projectID}` | `project edit` | R1 | 修改项目 |
| `project.list` | `GET` `/api.php/v2/projects` | `project list` | R0 | 获取项目列表 |
| `project.list_program` | `GET` `/api.php/v2/programs/{programID}/projects` | `project list --program <id>` | R0 | 获取项目集下的项目列表 |
| `project.delete` | `DELETE` `/api.php/v2/projects/{projectID}` | `project delete` | R3 | 删除项目 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
