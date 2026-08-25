# file · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `file.upload` | `POST` `/api.php/v2/files` | `file upload` | R1 | 上传附件 |
| `file.edit` | `PUT` `/api.php/v2/files/{fileID}` | `file edit` | R1 | 修改附件名称 |
| `file.delete` | `DELETE` `/api.php/v2/files/{fileID}` | `file delete` | R3 | 删除附件 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
