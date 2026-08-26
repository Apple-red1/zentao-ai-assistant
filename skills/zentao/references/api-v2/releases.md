# release · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `release.create` | `POST` `/api.php/v2/releases` | `release create` | R1 | 创建发布 |
| `release.edit` | `PUT` `/api.php/v2/releases/{releaseID}` | `release edit` | R1 | 修改发布 |
| `release.list_product` | `GET` `/api.php/v2/products/{productID}/releases` | `release list --product <id>` | R0 | 获取产品发布列表 |
| `release.delete` | `DELETE` `/api.php/v2/releases/{releaseID}` | `release delete` | R3 | 删除发布 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。

21.7.8 实测补充：创建和编辑时，当 `status=normal` 时，真实实例还要求 `releasedDate`（实际发布日期），CLI 使用 `--released-date` 传入；状态为 `wait` 时可不传该字段。编辑发布还必须同时保留 `productID` 与兼容字段 `product`，否则接口返回成功但发布会从产品列表中消失。
