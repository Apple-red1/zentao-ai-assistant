# user · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `user.create` | `POST` `/api.php/v2/users` | `user create` | R1 | 创建用户 |
| `user.edit` | `PUT` `/api.php/v2/users/{userID}` | `user edit` | R1 | 修改用户信息 |
| `user.list` | `GET` `/api.php/v2/users` | `user list` | R0 | 获取用户列表 |
| `user.view` | `GET` `/api.php/v2/users/{userID}` | `user view` | R0 | 获取用户详情 |
| `user.delete` | `DELETE` `/api.php/v2/users/{userID}` | `user delete` | R3 | 删除用户 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
