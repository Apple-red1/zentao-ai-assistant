# release · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `release.create` | `POST` `/api.php/v2/releases` | `release create` | R1 | 创建发布 |
| `release.edit` | `PUT` `/api.php/v2/releases/{releaseID}` | `release edit` | R1 | 修改发布 |
| `release.list_product` | `GET` `/api.php/v2/products/{productID}/releases` | `release list --product <id>` | R0 | 获取产品发布列表 |
| `release.delete` | `DELETE` `/api.php/v2/releases/{releaseID}` | `release delete` | R3 | 删除发布 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
