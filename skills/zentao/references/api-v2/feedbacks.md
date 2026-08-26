# feedback · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `feedback.create` | `POST` `/api.php/v2/feedbacks` | `feedback create` | R1 | 创建反馈 |
| `feedback.edit` | `PUT` `/api.php/v2/feedbacks/{feedbackID}` | `feedback edit` | R1 | 修改反馈 |
| `feedback.list_product` | `GET` `/api.php/v2/products/{productID}/feedbacks` | `feedback list --product <id>` | R0 | 获取产品反馈列表 |
| `feedback.view` | `GET` `/api.php/v2/feedbacks/{feedbackID}` | `feedback view` | R0 | 获取反馈详情 |
| `feedback.close` | `PUT` `/api.php/v2/feedbacks/{feedbackID}/close` | `feedback close` | R2 | 关闭反馈 |
| `feedback.activate` | `PUT` `/api.php/v2/feedbacks/{feedbackID}/activate` | `feedback activate` | R2 | 激活反馈 |
| `feedback.delete` | `DELETE` `/api.php/v2/feedbacks/{feedbackID}` | `feedback delete` | R3 | 删除反馈 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
