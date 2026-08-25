# product · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `product.create` | `POST` `/api.php/v2/products` | `product create` | R1 | 创建产品 |
| `product.edit` | `PUT` `/api.php/v2/products/{productID}` | `product edit` | R1 | 修改产品 |
| `product.list` | `GET` `/api.php/v2/products` | `product list` | R0 | 获取产品列表 |
| `product.list_program` | `GET` `/api.php/v2/programs/{programID}/products` | `product list --program <id>` | R0 | 获取项目集的产品列表 |
| `product.view` | `GET` `/api.php/v2/products/{productID}` | `product view` | R0 | 获取产品详情 |
| `product.delete` | `DELETE` `/api.php/v2/products/{productID}` | `product delete` | R3 | 删除产品 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
