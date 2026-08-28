# ZenTao 21.7.8 兼容性状态

官方 API v2 合同与目标实例兼容性是两个独立维度。本文件记录 2026-08-25 起在全新 ZenTao 21.7.8 实例上的真实验收结果；凭证仍只从本地 `.env` 读取，不写入仓库。

## 已验证

- 本地自动化全量测试：本轮变更后 API 专项与仓库级回归均通过；Catalog、Internal、CLI、Fake、Contract、CLI E2E 均为 120/120，真实 API 调用计数为 0。
- 真实只读 endpoint-level evidence：5 个 endpoint ID 通过（`token.login`、`product.list`、`project.list`、`bug.list_product`、`bug.list_project`），具体 case 记录在 compatibility evidence 文件中；不再使用无法追溯的“44/44”口径。
- 真实对象资源获取：`resource fetch --object-type product --object-id 2` 返回空资源成功；临时 Bug 的富文本保留同源 `/theme/default/images/main/logo.png`，`resource fetch --object-type bug --object-id 3` 成功流式下载 2,067 字节 PNG，落盘文件与直接服务器响应 SHA-256 一致；临时对象已清理。
- 真实写入和状态流：项目集、产品、项目、执行、构建、应用、需求、用户需求、业务需求、任务、测试用例、测试单、Bug、用户的创建，以及需求/业务需求关闭激活、任务开始完成关闭激活、Bug 解决关闭激活均已成功；Bug PUT 编辑在本实例上返回空响应且回读不变，已单独标为不支持。
- Project 真实场景：创建项目时未传产品会由目标自动创建同名产品；分支产品关联返回“分支不能为空”；项目编辑省略的可选配置可能被目标清空；项目集列表存在权限边界，项目列表的过滤/页码由目标回退；目标在已有执行下仍允许删除项目，未提供下游依赖保护。
- Execution 真实场景：目标会校验执行日期不超出项目边界；view/list 不返回产品/计划字段但产品 dynamics 可确认部分关联；编辑省略 `days` 或 `acl` 会清空目标值；多产品、阶段/运维产品关系存在目标侧不可见差异；目标在执行仍有下游任务时仍允许删除。
- Epic 真实场景：创建成功响应可能缺少 `id`，需通过产品列表回读；`pri` 是目标优先级字段；`change` 要求标题和 reviewer，spec/verify 中的 URL 与实体会被目标转为 HTML；启用评审时编辑省略 reviewer 会清空评审人，CLI 已改为写入前强制显式保留；duplicate 关闭要求 `duplicateStory`；分页、列表、查看、关闭、激活、删除均完成真实回读。目标允许删除仍有子项的父 Epic，子项会留下孤立 parent 引用。
- Requirement 真实场景：创建成功响应可能缺少 `id`，需通过产品列表回读；change 要求 reviewer，spec/verify 的 URL 与实体会被目标转为 HTML；启用评审时 edit 需显式 reviewer，省略的优先级会重置为目标默认值；duplicate 关闭要求 `duplicateStory`；parent 编辑返回空响应且未改变，跨产品父子创建被目标接受，删除父需求会留下孤立子项引用。
- Story 真实场景：创建、编辑、change、产品/项目/执行列表、详情、关闭、激活、删除均已真实执行并回读；目标 PUT edit 对省略 source/reviewer/assignee 采用替换/清空语义，省略优先级会重置，未把局部写入声称为安全保留；change 要求 reviewer 并会 HTML 化文本 URL/实体。项目 scope 可能返回 302，执行 scope 的关联字段与 view 不完全一致，且 API v2 没有原生项目/执行/计划 link/unlink endpoint；跨类型 Epic parent 会被目标接受，删除父 Story 会留下孤立子项。
- Task 真实场景：execution #40 不存在，使用已确认的 #10 完成 create/edit/list/view/start/finish/close/activate/delete；目标 edit 省略 priority 会重置为 0，start 要求非零 consumed/left，finish 按 currentConsumed 累加而非接受传入总值；任务描述 URL 会 HTML 化，无效 Story/负责人返回真实错误，无 pause endpoint，删除父任务会级联子任务。
- Test Case 真实场景：create、edit、产品/项目/执行列表、view、delete 均已真实执行并回读；create 可能返回空响应或 UNKNOWN_WRITE_RESULT 但对象已创建，客户端不伪造 ID；多步请求省略 `stepType` 时目标只保留第一步，适配器现为每个普通 step 自动补 `step`；PUT edit 实际要求 `type`，并对省略字段采用替换/清空语义，可能清空 product 和 steps，因此官方 edit surface 不支持安全的“仅改标题保留原内容”；无效 Story 返回真实错误，项目/执行不匹配被目标接受，删除带项目/执行关联的用例也未触发依赖保护。
- Test Task 真实场景：create、产品/项目/执行列表和逐对象 delete 均完成真实回读；目标接受 `productID/product`、可选 execution=0 以及跨产品 build/execution 组合。PUT edit 对现有列表 ID 一律返回 `Task does not exist`，标为 unsupported；DELETE 对本轮一个对象成功、其余对象同样返回该错误，无法安全清理剩余测试单；无 view、close、用例关联或报告 endpoint，本轮 fixture 保留并记录该目标限制。
- Build 真实场景：create/edit/项目列表/执行列表/delete 均完成真实回读；Unicode、空格和多行说明可保留，带查询参数的 SCM path 会被目标返回为 HTML `&amp;`；目标接受 system/product 与 execution/project 不一致、同一 execution 的重复名称会被拒绝；无 view、submit-test、merge、pass、rollback endpoint。删除要求 `--yes`，但对仍被 9 个 Test Task 引用的 Build #35 仍返回成功并隐藏构建，下游测试单继续保留旧引用；空响应按 `API_ERROR` 处理，UNKNOWN_WRITE_RESULT 先通过显式列表确认。
- Release 真实场景：create/edit/产品列表/delete 均完成真实回读；wait 与 normal 可用，normal 要求 `releasedDate`，而 fail/terminate 在目标上即使带 `releasedDate` 仍返回“实际发布日期不能为空”；多 Build 会在列表中展开重复行，page=2 回退第 1 页，`browse=wait` 未过滤 normal；跨产品 Build 可能只保留原始引用而无法展开；无 view/activate/close/rollback endpoint，重复名称被拒绝，删除仍被 System `latestRelease` 引用的发布也被允许。
- System 真实场景：create/edit/产品列表均完成真实回读；create 常返回 success 但没有 id，适配器报告 API_ERROR 后通过列表找回对象；集成应用要求 child，child 顺序保留，非法/self child 被目标接受，名称全局唯一，分页第 2 页回退，描述 URL 的 `&` 被 HTML 化；edit 不提供 integrated，且 System API 无 view/delete/close/activate，本轮 fixture 无法通过官方 API 清理。
- User 真实场景：create/edit/list/view/delete 均完成真实回读；create 未指定 vision 时默认 `rnd`，目标 edit 除 account 外还要求 realname/visions；dept #3 不存在，group 写入虽被接受但 list/view 不返回 group 字段；分页不足时第 2 页回退；view 不返回 password，UNKNOWN/空响应先通过列表确认；删除被 Test Task owner 引用的用户仍成功，下游保留旧 owner，当前实例无依赖保护。本轮用户 fixture 已逐个删除，历史用户保留。
- 本轮创建的数据先用于后续真实编辑与列表回读；已清理可确认且不影响依赖的测试叶子对象，承载测试的产品/项目层级仍保留；系统没有 `system.delete` 端点。

## 已同步的 21.7.8 差异

`endpoints.json` 的 compatibility 状态由 `skills/zentao/references/compatibility/zentao-21.7.8.json`
逐条校验。当前 120 个 endpoint 的机器统计为：

```text
      observed      = 92
      unsupported   = 18
      not_observed  = 10
```

只有有真实 evidence 的条目才标为 `observed`；没有 endpoint-level evidence 的条目
保持 `not_observed`，不会因为历史“44/44”叙述而批量升级。已记录的兼容差异包括：

- `test-case.create`、`test-task.create`：服务端要求同时接收 `productID` 和兼容字段 `product`。
- `user.create`：服务端要求 `visions`，CLI 默认发送 `rnd`。
- `requirement.change`：服务端实际要求 `reviewer`；`user.edit`：服务端实际要求 `account`。
- `requirement.edit`、`epic.edit`：真实实例接受分类字符串，CLI 同时兼容字符串和数字 ID。
- `product-plan.create`、`product-plan.edit`：真实实例创建/编辑时分别要求兼容字段 `product`、`productID`，编辑还必须保留当前 `status`；`branchID` 与 `branch` 同时发送。
- `release.create`、`release.edit`：`status=normal` 时要求 `releasedDate`；编辑还必须同时保留 `productID` 与 `product`。
- `bug.create`：服务端实际要求同时接收官方字段 `productID` 和兼容字段 `product`；CLI 的一个 `--product` 参数会同时发送两者，否则创建成功后回读的产品归属可能为 `0`。目标实例不会校验 `project`、`execution`、`story` 的跨产品一致性，调用方必须先只读确认关系，不能把服务端接受请求描述成关系合法。
- `product.create`、`product.edit`：官方字段表将 `desc` 标为数组，但目标 21.7.8 的实际保存路径把单元素列表写成字面量 `Array`；适配器按真实文本合同发送标量描述，回读可保留中文文本。
- `bug.list_execution`：目标实例在 `browseType=unresolved` 时仍返回 resolved/closed 行；调用方必须在足够宽的 execution 列表回读后按真实 `status` 过滤，并明确分页/截断情况。
- `story.create`：官方参数将 `reviewer` 标为可选，但本实例实际要求评审人；首次请求缺少该字段时返回“『评审人』不能为空”，补充 `--reviewer admin` 后创建成功。
- `bug.edit`：目标实例对官方 `PUT /bugs/{bugID}` 返回空响应且回读不变；官方编辑合同也不包含 `assignedTo`，因此当前不将其作为可用的 Bug 转交能力。
- `system.create`：本实例返回 `status=success` 但不返回 `id`，对象仍会被创建；当前 CLI 因创建合同要求 `id` 而报告错误，必须通过只读列表确认实际结果。
- `bug.activate`：官方参数将 `openedBuild` 标为可选，但本实例实际要求该字段；应从当前 Bug 的影响/解决版本回读并显式传入，不能无依据猜测或重放。该端点只接受已解决或已关闭 Bug，不能用于保持 active 状态的负责人转派；本实例未提供可用的独立 active-Bug 转派端点。
- `epic.create`：目标返回 `status=success` 但可能缺少 `id`，对象仍会被创建；CLI 报告 `API_ERROR`，随后必须用 `epic list --product` 确认实际结果。
- `epic.edit`、`epic.change`：目标使用 `pri` 表示优先级，接受分类字符串；启用评审的实例对编辑请求要求 reviewer，省略字段会清空评审人，故 CLI 在 HTTP 前拒绝缺少 reviewer 的编辑。`change` 的 spec/verify 会被目标做 HTML 链接和实体规范化。
- `epic.close`：`closedReason=duplicate` 时目标要求 `duplicateStory`；无效的重复目标返回真实业务错误。
- `epic.delete`：目标允许删除仍被子 Epic 引用的父项，子项保留旧 parent ID；本记录不把服务端成功描述为依赖约束已生效。
- `requirement.create`：目标返回 `status=success` 但可能缺少 `id`，对象仍会被创建；CLI 报告 `API_ERROR`，随后必须用 `requirement list --product` 确认实际结果。
- `requirement.edit`、`requirement.change`：目标接受分类字符串；启用评审时编辑必须显式传 reviewer，CLI 缺少 reviewer 会在 HTTP 前拒绝；目标对省略的 `pri` 采用默认值替换。change 的 spec/verify 会被 HTML 化。
- `requirement.close`：`closedReason=duplicate` 时目标要求 `duplicateStory`；#88 等不存在目标返回真实错误，未猜测或关闭对象。
- `requirement.edit` 的 parent：真实目标返回空响应且回读不变，未通过其他接口伪造 parent 迁移。
- `story.edit`：目标对省略的 `source`、`reviewer`、`assignee` 可能清空，对省略 `pri` 会重置为 3；执行局部编辑前必须显式读取并提交要保留的字段，CLI 不做隐式第二个业务 endpoint。
- `story.change`：目标要求 reviewer；文件输入中的 URL、HTML 实体会被目标标准化，回读以服务端内容为准。
- `story.list_project`：本实例对项目 scope 可能返回 302 且无正文，未把它包装成空列表或权限成功。
- `story` 关联边界：目标没有原生 link/unlink endpoint；创建时 project/execution 字段在 view/list 中可能不一致，跨类型 Epic parent 也被目标接受，因此调用方必须显式记录真实兼容性，不能声称关系校验已完成。
- `task.start`：目标要求 `consumed` 或 `left` 至少一个非零；用户未给出工时不能无依据填默认值，应返回真实校验错误。
- `task.finish`：`currentConsumed` 是本次新增工时，目标按既有 consumed 累加；不能把 `--consumed` 的传入值描述为最终总工时，需回读确认。
- `task.edit`：省略 priority 会重置为目标默认值 0；其他字段以真实 view 回读为准，不能把局部写入包装成全字段保留。
- `task` 关系/生命周期：当前 API v2 没有 pause/continue；删除仍有子任务的父任务会由目标级联删除子任务，已按真实回读记录。
- `test-case.create`：目标要求同时发送 `productID` 和兼容字段 `product`；多步请求若不发送逐项 `stepType` 会静默丢弃后续步骤，适配器已自动补普通 `step` 类型。
- `test-case.edit`：目标实际要求 `type`，并把省略字段按替换/清空处理；实测省略 product 会将其置 0，省略 steps 会清空步骤，不能把 title-only 编辑声称为安全保留。
- `test-case.list_*`、`test-case.view`、`test-case.delete`：产品/项目/执行列表、详情和逐对象删除均完成真实回读；项目列表对部分跨项目记录返回空结果，目标删除有项目/执行关联的用例未实施依赖保护。
- `test-task.create`：目标要求同时发送 `productID` 和 `product`；可选 execution=0 被接受，build/execution 跨产品组合也被接受，调用方不能把服务端接受描述成关系校验通过。
- `test-task.edit`：目标对现有列表中的测试单 ID 一律返回 `Task does not exist`，owner、日期、状态、名称、类型和 build 编辑均未改变列表；本实例将官方 edit endpoint 标为 unsupported。
- `test-task.delete`：本轮一个测试单删除成功，但其他由同一 create 流程产生的 ID 均返回 `Task does not exist` 并继续出现在列表；未改用 v1、数据库或其他接口，剩余 fixture 因此保留。
- `build.create`、`build.edit`、`build.list_project`、`build.list_execution`、`build.delete`：真实创建、编辑、项目/执行查询和逐对象删除均完成回读；SCM query path 的 `&` 被目标 HTML-escape，关系组合不做服务端校验，重复名称由目标拒绝；Build delete 不阻止下游 Test Task 引用。
- `release.create`、`release.edit`、`release.list_product`、`release.delete`：真实创建、编辑、产品列表和逐对象删除均完成回读；normal 要求 `releasedDate`，fail/terminate 在本实例不可用；多构建列表会重复行，分页/`browse` 过滤会被目标回退或忽略，跨产品 Build 关联无法展开，删除不实施 System latestRelease 依赖保护。
- `system.create`、`system.edit`、`system.list_product`：真实创建、编辑和产品列表均完成回读；创建 success 缺少 id，集成空 child 被拒绝，非法/self child 被接受，名称按全局唯一校验，分页回退且描述会 HTML-escape；没有官方 System delete/view/lifecycle endpoint，fixture 不能借其他资源接口清理。
- `user.create`、`user.edit`、`user.list`、`user.view`、`user.delete`：真实创建、编辑、列表、详情和逐对象删除均完成回读；目标 edit 实际要求 realname/visions，view 不返回 password，group/部门关系缺少可用读回字段，删除不实施下游 Test Task 依赖保护。

## 当前实例限制

- 反馈与工单模块：目标实例对创建、列表、详情及生命周期请求返回空响应（CLI 旧逻辑会渲染为 `status: success`）；产品配置探针返回 `Feedback does not exist.`，确认当前 21.7.8 未启用对应模块。代码现会把缺少对象字段的响应报告为 `API_ERROR`，而不是假成功。
- 文件模块：在真实 21.7.8 上，v2 `file.upload`/`file.edit` 仍返回空响应，官方 v2 上传能力标注为 v22.0 及以上；但页面网络观察确认附件实际由 Bug 编辑表单的 multipart `files[]` 写入。基础 CLI 现在仅在 v2 上传空响应、一次 API 回读确认未落库后，向固定的 `bug/edit` URL 提交页面表单，并再次回读确认。Bug `80` 的 `sample.txt` 已真实落库，附件 ID 为 2，大小 23 字节；`resource fetch` 下载成功且与源文件 SHA-256 均为 `82b5b5e695bdfd144be17d27f4fbc11a5855012bd9d9eb51c6d3cde8255d5b4e`，单对象 ZIP 的 manifest 和对象均 `complete=true`，ZIP 内字节一致。不存在附件的真实删除仍返回业务错误；未执行删除测试数据。

发布前自动化门槛见 [release-checklist.md](../release-checklist.md)：完整测试必须在 Fake 环境达到 120/120，且真实 API 调用计数为 0。官方合同快照与 21.7.8 观察分别见 `skills/zentao/references/api-v2/official-contract.json` 和 `skills/zentao/references/compatibility/zentao-21.7.8.json`；文档统计必须与机器 evidence contract 一致。

## 对象关联资源获取：已完成真实 21.7.8 复验

本次新增 `resource fetch` 后，本地 Fake 已覆盖附件区 + 富文本资源发现、HTTP 二进制流式落盘、data URI、同名不覆盖、部分失败、同源重定向和跨源重定向拦截。官方 120 endpoint 覆盖集合保持不变。

本次使用项目 `.env` 连接真实实例完成对象详情读取和同源富文本图片下载。已观察到：

- 富文本中的同源绝对/根相对图片 URL 可被发现并下载；资源 GET 携带 API Token 即可成功；
- 返回的 `Content-Type: image/png` 和二进制内容均按流式方式保存，未发生内容改写；
- 21.7.8 实例的 v2 `file upload` 写入端点仍返回空响应，但通过固定 Bug 编辑页面的 `files[]` 兼容路径已真实生成附件元数据；`resource fetch` 对 Bug `80` 下载附件成功，且批量导出 ZIP 的 manifest、附件文件和字节校验均完整；
- 本次未发现真实资源重定向链，重定向和跨源拦截仍由 Fake E2E 覆盖。

上述真实观察不改变官方 120 endpoint catalog：`file.upload` 的 v2 endpoint 仍记录为
unsupported，页面兼容路径是基础 CLI 的内部实现，不是新增 endpoint。为保留真实验证
证据，本轮创建的测试 Bug `79`、`80` 未执行删除，需用户明确指定具体 ID 后再按 R3 合同清理。

## 独立评论功能（Issue #52，2026-08-28）

本次使用项目 `.env` 中配置的专用 ZenTao 21.7.8 实例完成真实写入和只读回读；自动化
Fake 不参与以下结果。评论页面和内嵌图片均通过现有 `LegacyWebClient`，没有新增 API
endpoint，也没有执行删除清理这些专用验收数据。

| 能力 | 真实对象 | 写后 action / 文件证据 | 结果 |
|---|---:|---|---|
| 十种对象评论正文 | Bug 79、Story 5、Product 2、Task 3、Execution 10、Project 8、Test-task 16、Product-plan 7、Release 1、Build 55 | action `4843`、`4864`、`4867`、`4870`、`4873`、`4875`、`4889`、`4892`、`4894`、`4896`（按对象顺序） | 均成功，回读确认 `action=commented`、对象类型/ID和正文 |
| Bug/Story 重复普通附件 | Bug 79、Story 5 | Bug action `4899`，file `8/9`；Story action `4902`，file `10/11` | 均成功，中文文件名、大小和 comment action 归属回读确认 |
| Bug 单张内嵌图片 | Bug 79 | action `4941`，inline file `17` | `ajaxUpload` 单次成功，评论回读确认同源图片 URL |
| 评论资源显式回读 | Bug 79、Story 5 | `resource fetch --include-comments`；Bug 评论资源含 action `4899`/inline `4941` 等，Story 含 action `4902` 的 file `10/11` | 两个命令均 exit `0`，`partial_failures=[]`，下载文件字节可读 |

用于资源字节核对的验收文件 SHA-256：内嵌 PNG（Bug file `17`）为
`65d3e2eafcc403c84f500dc83d8e774e240eae611fd76cf15f4515784b8643d3`；Story `附件-A.txt`
（file `10`）为 `990c40f4024db3d59454f4a43a030667d04d613b54ad46fd13354e64a987ed`，
`附件-B.txt`（file `11`）为 `4797c36988bf0024ee4b1d974c760018c021ee03507d7543019bcef47a46e42e`。
资源落盘仍位于当前 scope 的 `.tmp/zentao-resources/`，验收输出未写入仓库。
