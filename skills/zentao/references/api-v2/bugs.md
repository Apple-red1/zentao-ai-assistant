# bug · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `bug.create` | `POST` `/api.php/v2/bugs` | `bug create` | R1 | 创建 Bug |
| `bug.edit` | `PUT` `/api.php/v2/bugs/{bugID}` | `bug edit` | R1 | 修改 Bug |
| `bug.list_product` | `GET` `/api.php/v2/products/{productID}/bugs` | `bug list --product <id>` | R0 | 获取产品 Bug 列表 |
| `bug.list_project` | `GET` `/api.php/v2/projects/{projectID}/bugs` | `bug list --project <id>` | R0 | 获取项目 Bug 列表 |
| `bug.list_execution` | `GET` `/api.php/v2/executions/{executionID}/bugs` | `bug list --execution <id>` | R0 | 获取执行 Bug 列表 |
| `bug.view` | `GET` `/api.php/v2/bugs/{bugID}` | `bug view` | R0 | 获取 Bug 详情 |
| `bug.resolve` | `PUT` `/api.php/v2/bugs/{bugID}/resolve` | `bug resolve` | R2 | 解决 Bug |
| `bug.close` | `PUT` `/api.php/v2/bugs/{bugID}/close` | `bug close` | R2 | 关闭 Bug |
| `bug.activate` | `PUT` `/api.php/v2/bugs/{bugID}/activate` | `bug activate` | R2 | 激活 Bug |
| `bug.delete` | `DELETE` `/api.php/v2/bugs/{bugID}` | `bug delete` | R3 | 删除 Bug |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。

ZenTao 21.7.8 实测补充：创建 Bug 时服务端需要同时接收官方字段 `productID` 和兼容字段
`product`；CLI 仍只暴露一个 `--product`，运行时会同时发送两个字段，以确保 Bug 的产品归属
在回读中保持正确。

目标实例不会在 `bug.create` 中校验 `project`、`execution`、`story` 之间的跨产品一致性；调用方
必须先通过只读查询确认这些关系，不能把服务端接受请求误认为关系合法。CLI 按用户明确提供的
ID 发送单一创建 endpoint，不会猜测或替换关联对象。

目标实例的 `PUT /bugs/{bugID}` 编辑请求返回空响应且回读不变，且官方编辑合同不包含
`assignedTo`；因此 `bug edit` 不提供负责人参数。对已解决 Bug 的负责人转交应沿用当前
解决版本调用 `bug resolve --resolution ... --resolved-build ... --assignee ...`，并在写后回读状态。
`bug activate` 只适用于已解决或已关闭 Bug；在 active 状态下不能作为“只转负责人、保持 active”
的替代接口，目标实例也未提供可用的独立转派 endpoint。

## 步骤内嵌图片兼容能力

`bug create` 和 `bug edit` 可重复接受 `--steps-inline-image <local-image>`。这是针对
ZenTao 21.7.8 编辑器页面的兼容路径，不是新的 API v2 endpoint：读取固定 Bug 表单取得
`uid`，兼容该字段的 `hidden` 和 `text` 输入形态，但只按精确字段名受控读取；其它可见输入
不会纳入 payload。经同源 `file/ajaxUpload` 上传本地图片，把受控 `<img src>` 片段随
`steps` 页面表单提交，再通过现有 `bug.view` 回读确认步骤引用和 Bug 文件归属。普通步骤
文本先转义；uid 缺失、空值或冲突，或上传、表单写入、回读无法安全确认时失败且不回退到
评论、不自动重试。

Bug 列表的官方 `browseType` 范围按 scope 区分：产品支持
`all | unclosed | assignedtome | openedbyme | assignedbyme`；项目和执行支持
`all | unresolved`。CLI 的 `assigned-to-me`、`opened-by-me`、`assigned-by-me`
会映射为对应 API 值。详见独立官方合同快照和 #9 的 API v2 deep-link 证据。

## Bug Web URL

`bug web-url` 是本地只读组合能力，按固定禅道路由
`ZENTAO_BASE_URL/index.php?m=bug&f=view&bugID=<id>` 生成单个或批量链接，不发送页面请求，也不启动浏览器。
