# program · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `program.create` | `POST` `/api.php/v2/programs` | `program create` | R1 | 创建项目集 |
| `program.edit` | `PUT` `/api.php/v2/programs/{programID}` | `program edit` | R1 | 修改项目集 |
| `program.list` | `GET` `/api.php/v2/programs` | `program list` | R0 | 获取项目集列表 |
| `program.view` | `GET` `/api.php/v2/programs/{programID}` | `program view` | R0 | 获取项目集详情 |
| `program.delete` | `DELETE` `/api.php/v2/programs/{programID}` | `program delete` | R3 | 删除项目集 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
