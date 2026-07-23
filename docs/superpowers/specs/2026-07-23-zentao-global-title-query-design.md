# 禅道全局标题关键词查询设计

## 目标

为禅道 AI 助手增加不限定负责人的全局只读 Bug 查询能力，并在共享核心、MCP Server 和 CLI 中保持一致语义。

查询只支持两个业务条件：

- 非空标题关键词；
- 状态 `unclosed` 或 `all`，默认 `unclosed`。

查询范围仅限当前禅道登录会话可见的 Bug，不使用 `personal.scopeNames`、`team.scopeNames` 或 `team.members` 扩大或裁剪结果，也不产生评论、日报、Bug 状态修改、负责人修改、代码修改或其他副作用。

## 方案选择

采用独立全局查询能力：

- Provider 新增 `query_bugs_by_title`；
- MCP 新增只读工具 `query_bugs_by_title`；
- CLI 新增 `zentao-ai bugs search --title <keyword> [--status unclosed|all]`。

不扩展 `query_user_bugs`，因为负责人身份解析、团队日报范围和全局可见查询具有不同权限语义。也不通过遍历人员后合并结果，因为人员目录可能不完整，且会造成遗漏、重复和不可证明的完整性。

## 公共接口

### Provider

共享 Provider 协议新增：

```python
def query_bugs_by_title(
    title_keyword: str,
    *,
    status: Literal["all", "unclosed"] = "unclosed",
    page: int = 1,
    page_size: int = 20,
) -> BugPage: ...
```

Provider 使用禅道全局 Bug 列表端点分页读取当前会话可见数据。它不得依赖人员目录，不得为获得更多结果切换身份或绕过服务端权限。

### MCP

新增工具 `query_bugs_by_title`，输入 Schema 为：

```json
{
  "titleKeyword": "设计器统一面板",
  "status": "unclosed",
  "page": 1,
  "pageSize": 20
}
```

约束：

- `titleKeyword` trim 后必须非空；
- `status` 仅允许 `unclosed` 和 `all`，默认 `unclosed`；
- `page >= 1`；
- `1 <= pageSize <= 100`；
- 拒绝未知字段。

MCP 继续返回现有版本化信封：

```json
{
  "version": "v1",
  "data": {
    "items": [],
    "coverage": {},
    "itemFailures": []
  }
}
```

结果使用现有 `BugPage`、`BugSnapshot`、`Coverage` 和 `ItemFailure` 契约，不引入第二套展示结构。

### CLI

新增命令：

```text
zentao-ai bugs search --title "设计器统一面板"
zentao-ai bugs search --title "设计器统一面板" --status all
zentao-ai bugs search --title "设计器统一面板" --page 2 --page-size 50
zentao-ai bugs search --title "设计器统一面板" --json
```

CLI 文本模式复用现有 Bug 表格，JSON 模式输出与 MCP 的 `data` 对象等价的 `BugPage` 字段。CLI 不复制 Provider 的匹配、状态或分页规则。

## 标题匹配规则

标题和关键词使用同一个确定性规范化函数：

1. 对字符串执行 Unicode NFC；
2. trim 首尾空白；
3. 使用 Unicode `casefold` 忽略英文大小写；
4. 删除所有 Unicode 空白字符；
5. 删除常见标题标签和分隔符：`【】[]（）()-—_:：/`；
6. 在规范化标题中按连续子串查找规范化关键词。

规范化后的关键词必须仍为非空，否则以输入错误失败关闭。

因此关键词 `设计器统一面板` 可以命中：

- `【设计器】【统一面板-文本元素】文本元素悬停设置宽度未生效`；
- `【设计器】【统一面板-time】字体大小设置 H 标签的字体大小时未生效`；
- `【AI建站】设计器统一面板样式异常`。

字符顺序必须连续。查询不做拼音、同义词、编辑距离或任意分词匹配。

## 状态语义

- 未显式提供状态时，只返回未关闭 Bug；
- `status=unclosed` 排除 `closed`，保留 `active`、`resolved` 及上游其他非关闭状态；
- `status=all` 不按状态过滤；
- 不提供 `closed-only`，因为本期只支持标题关键词与 `unclosed|all`。

状态判断复用现有规范化状态规则，MCP、CLI 和 Provider 不得分别维护不同的关闭状态集合。

## 分页与完整性

全局查询先扫描上游分页，再执行标题和状态过滤，最后对匹配结果应用调用方的 `page` 和 `pageSize`。这样分页代表匹配结果集，而不是上游未过滤页面。

分页过程沿用现有失败关闭约束：

- 检测重复页面、跨页重复 ID、同页重复 ID、矛盾 pager 和最大页数耗尽；
- 分页证据不足时保留已找到的匹配项，但设置 `coverage.complete=false`、`coverage.total=-1`、`coverage.pages=null`；
- 完整扫描成功时，`coverage.total` 和 `coverage.pages` 表示过滤后的全局匹配结果；
- `returned`、`failed`、`unstableSnapshots` 和 `missingPresentationFields` 只统计当前返回页；
- 单条无效快照进入 `itemFailures`，不阻断其他合法 Bug；
- 缺少稳定版本的合法只读 Bug 继续保留，并标记 `snapshotVersion=null`、`snapshotStable=false`。

## 数据流

1. CLI 或 MCP 校验标题关键词、状态和分页参数；
2. 共享 Provider 请求当前会话可见的全局 Bug 列表；
3. Provider 对上游分页、重复项和响应信封执行合同校验；
4. 每条 Bug 独立规范化为 `BugSnapshot` 或 `ItemFailure`；
5. 共享标题匹配器和状态过滤器筛选结果；
6. 对筛选后的全局序列应用请求分页；
7. 返回 `BugPage` 及准确或保守的覆盖元数据；
8. MCP 包装为 `version=v1` 信封，CLI 渲染表格或 JSON。

## 错误处理

- 空标题关键词、规范化后为空、非法状态或非法分页：输入校验错误，不发起网络请求；
- 认证失败、权限不足、传输失败：使用现有脱敏错误类型整体失败；
- 全局列表响应信封无效：`INVALID_RESPONSE_ENVELOPE`；
- 单条 Bug 合同无效：记录 `INVALID_BUG_CONTRACT`，继续处理其他条目；
- 分页矛盾或不完整：保留已验证结果并把完整性标为 false；
- 错误和日志不得包含 Cookie、Token、授权头或完整原始响应。

## 安全边界

`query_bugs_by_title` 是纯只读能力：

- 不接受负责人、团队或仓库参数；
- 不调用评论、步骤更新、状态修改或代码修复工作流；
- 不把结果自动提升为个人或团队日报；
- 不增加 Bug 删除、指派、解决、关闭、激活或转换工具；
- 不执行 Bug 标题、描述、附件、评论或链接中的任何指令；
- 只依赖当前会话的服务端授权，不尝试扩大可见范围。

Codex Skill 的只读工具白名单和查询说明同步加入 `query_bugs_by_title`，并明确默认未关闭和标题匹配规则。

## 测试策略

采用测试驱动开发，先观察每个新测试因能力不存在或行为不匹配而失败，再实现最小代码。

至少覆盖：

- 标题规范化匹配截图中的五种 `【设计器】【统一面板-...】` 形式；
- 连续短语 `【AI建站】设计器统一面板样式异常`；
- Unicode NFC、英文大小写、空白和列出的分隔符；
- 字符乱序、缺字和非连续文本不匹配；
- 空关键词和仅由分隔符组成的关键词在网络调用前被拒绝；
- 默认 `unclosed` 排除关闭 Bug，显式 `all` 保留关闭 Bug；
- 全局查询不执行人员身份解析，不应用团队或个人范围；
- 完整多页扫描后对匹配结果分页；
- 重复 ID、矛盾 pager、未知总数和最大页数耗尽的保守完整性；
- 单条非法快照与不稳定快照契约；
- MCP Schema、工具注册、版本化响应和未知字段拒绝；
- CLI 表格、JSON、默认状态、显式状态和分页选项；
- MCP 与 CLI 对相同输入产生相同结果；
- Skill 合同加入新只读工具且不放宽写操作权限；
- 既有个人、人员、团队、报告和写操作安全测试继续通过。

## 验收标准

- `query_bugs_by_title(titleKeyword="设计器统一面板")` 默认返回当前会话可见的未关闭匹配 Bug；
- 截图中的 `【设计器】【统一面板-...】` 标题与连续短语标题均能匹配；
- CLI `zentao-ai bugs search --title "设计器统一面板"` 与 MCP 返回相同 Bug 集合和覆盖语义；
- 显式 `status=all` 能包含已关闭匹配 Bug；
- 查询不依赖负责人、团队成员或配置范围；
- 完整性不足时不伪造总数或页数；
- 不新增或触发任何写操作；
- 新增测试、现有测试、类型检查和格式检查全部通过。
