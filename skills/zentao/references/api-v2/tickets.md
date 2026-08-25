# ticket · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `ticket.create` | `POST` `/api.php/v2/tickets` | `ticket create` | R1 | 创建工单 |
| `ticket.edit` | `PUT` `/api.php/v2/tickets/{ticketID}` | `ticket edit` | R1 | 修改工单 |
| `ticket.list_product` | `GET` `/api.php/v2/products/{productID}/tickets` | `ticket list --product <id>` | R0 | 获取产品工单列表 |
| `ticket.view` | `GET` `/api.php/v2/tickets/{ticketID}` | `ticket view` | R0 | 获取工单详情 |
| `ticket.close` | `PUT` `/api.php/v2/tickets/{ticketID}/close` | `ticket close` | R2 | 关闭工单 |
| `ticket.activate` | `PUT` `/api.php/v2/tickets/{ticketID}/activate` | `ticket activate` | R2 | 激活工单 |
| `ticket.delete` | `DELETE` `/api.php/v2/tickets/{ticketID}` | `ticket delete` | R3 | 删除工单 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
