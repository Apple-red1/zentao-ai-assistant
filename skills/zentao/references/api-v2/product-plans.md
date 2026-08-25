# product-plan · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `product-plan.create` | `POST` `/api.php/v2/productplans` | `product-plan create` | R1 | 创建产品计划 |
| `product-plan.edit` | `PUT` `/api.php/v2/productplans/{planID}` | `product-plan edit` | R1 | 修改产品计划 |
| `product-plan.list_product` | `GET` `/api.php/v2/products/{productID}/productplans` | `product-plan list --product <id>` | R0 | 获取产品计划列表 |
| `product-plan.view` | `GET` `/api.php/v2/productplans/{planID}` | `product-plan view` | R0 | 获取产品计划详情 |
| `product-plan.delete` | `DELETE` `/api.php/v2/productplans/{planID}` | `product-plan delete` | R3 | 删除产品计划 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
