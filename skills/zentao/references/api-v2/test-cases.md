# test-case · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `test-case.create` | `POST` `/api.php/v2/testcases` | `test-case create` | R1 | 创建测试用例 |
| `test-case.edit` | `PUT` `/api.php/v2/testcases/{caseID}` | `test-case edit` | R1 | 修改测试用例 |
| `test-case.list_product` | `GET` `/api.php/v2/products/{productID}/testcases` | `test-case list --product <id>` | R0 | 获取产品测试用例列表 |
| `test-case.list_project` | `GET` `/api.php/v2/projects/{projectID}/testcases` | `test-case list --project <id>` | R0 | 获取项目测试用例列表 |
| `test-case.list_execution` | `GET` `/api.php/v2/executions/{executionID}/testcases` | `test-case list --execution <id>` | R0 | 获取执行测试用例列表 |
| `test-case.view` | `GET` `/api.php/v2/testcases/{caseID}` | `test-case view` | R0 | 获取测试用例详情 |
| `test-case.delete` | `DELETE` `/api.php/v2/testcases/{caseID}` | `test-case delete` | R3 | 删除测试用例 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。
