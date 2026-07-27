# 禅道 21.7.8 Codex 插件设计

## 1. 目标

将当前仓库从“设计文档和安全基线”补全为一个可在 Codex 中安装的禅道插件。使用者从 GitHub 拉取仓库后，在已经安装 Codex、Python 3.11+ 且能够访问禅道的前提下，应能在三分钟内完成安装和首次配置。

首版必须支持：

- 配置禅道地址、个人账号、密码和团队成员；
- 一句话查询自己的未关闭 Bug 及汇总情况；
- 一句话查询本地配置团队成员的未关闭 Bug 及汇总情况；
- 按姓名或账号查询未配置的外部人员 Bug；
- 按状态、指派人、创建人、产品、项目、优先级、严重程度、类型、关键词和日期范围组合查询；
- 查询单个 Bug 的完整详情；
- 对单个 Bug 添加备注、编辑允许字段、激活和指派；
- Token 缺失或失效后使用本地账号密码自动重新登录；
- 提供真实、完整的 README、安装、配置、功能、安全和故障排查文档。

首版不创建、删除、解决或关闭 Bug，不执行代码修复、定时任务或团队自动写入。删除 Bug 永久不注册为工具。

## 2. 方案选择

采用“Codex Skill + 插件内置 MCP 配置 + 本地 Python MCP Server”的单仓库方案。

- Skill 负责理解自然语言、选择工具、格式化结果和执行交互安全规则。
- MCP Server 负责认证、用户解析、分页查询、过滤、Bug 写操作和结构化错误。
- Python 核心包是业务逻辑的唯一来源，安装脚本和测试复用同一实现。
- Codex 插件只声明技能和 MCP 启动入口，不在 Skill 中复制 HTTP 或认证逻辑。

不直接采用禅道通用 MCP，因为团队成员别名、跨范围聚合、Token 重登和精确写入边界仍需要专用适配。不采用 Skill 直接调用零散脚本，因为其分页、错误恢复和秘密管理难以可靠测试。

## 3. 仓库结构

```text
zentao-ai-assistant/
├── .agents/plugins/marketplace.json
├── .github/workflows/ci.yml
├── README.md
├── pyproject.toml
├── config/zentao.example.yaml
├── docs/
│   ├── installation.md
│   ├── configuration.md
│   ├── features.md
│   ├── security.md
│   └── troubleshooting.md
├── plugins/zentao-ai-bug/
│   ├── .codex-plugin/plugin.json
│   ├── .mcp.json
│   └── skills/zentao-ai-bug/SKILL.md
├── scripts/
│   ├── install.sh
│   └── install.ps1
├── src/zentao_ai/
│   ├── auth.py
│   ├── config.py
│   ├── users.py
│   ├── bugs.py
│   ├── actions.py
│   ├── client.py
│   ├── models.py
│   ├── server.py
│   └── cli.py
└── tests/
    ├── unit/
    ├── contract/
    ├── integration/
    └── e2e/
```

插件名沿用现有设计中的 `zentao-ai-bug`，Python 包和本地命令使用 `zentao-ai-assistant` 与 `zentao-ai`。

## 4. 三分钟安装体验

README 首屏只保留必要步骤，并分别提供 macOS/Linux 与 Windows 命令。

预期流程：

1. 从 GitHub 克隆仓库并进入目录。
2. 运行 `scripts/install.sh` 或 `scripts/install.ps1`。
3. 安装脚本创建隔离的 Python 环境、安装 `zentao-ai` 命令、注册仓库 Marketplace，并安装 `zentao-ai-bug` 插件。
4. 安装脚本启动 `zentao-ai setup`，依次询问禅道地址、账号、密码和团队成员姓名或账号。
5. `zentao-ai doctor` 验证配置、登录、API 2.0、成员解析、MCP 启动和 Codex 插件可见性。
6. 用户重启 Codex 或新建任务后直接使用自然语言查询。

安装脚本必须幂等。重复执行时更新本地环境和插件，不覆盖已有配置；升级后再次运行 `doctor`。

## 5. 本地配置

默认配置文件为：

```text
~/.codex/zentao-ai-bug/config.yaml
```

项目可通过 `ZENTAO_CONFIG` 指向其他配置文件。示例结构：

```yaml
version: 1
zentao:
  base_url: "https://zentao.example.com"
  api_version: "v2"
  account: "my-account"

team:
  members:
    - name: "张三"
      account: "zhangsan"
    - name: "李四"
      account: "lisi"

query:
  default_status: "unresolved"
  page_size: 100
  max_results: 500

writes:
  enabled: true
```

密码和 Token 不进入 YAML。`zentao-ai setup` 将密码写入操作系统凭据库，将 Token 写入同一安全存储；无可用凭据库时允许使用仅存在于当前进程环境中的 `ZENTAO_PASSWORD`，但不自动生成含明文密码的 `.env` 文件。

团队成员允许先输入姓名。首次配置或 `doctor` 会通过禅道用户列表解析账号，并将姓名与账号同时保存。重名时必须让用户选择，不能猜测。团队外人员无需预先配置，可在查询语句中直接使用姓名或账号。

## 6. 认证与 Token 生命周期

禅道 21.7.8 使用 API 2.0：

- 登录：`POST /api.php/v2/users/login`；
- 请求体只包含 `account` 和 `password`；
- 后续请求在 `Token` 请求头中携带 Token。

认证流程：

1. 从安全存储读取缓存 Token；没有 Token 时登录。
2. 使用 Token 发起 API 请求。
3. 收到 401 时立即使旧 Token 失效，使用账号密码重新登录一次。
4. 新 Token 写回安全存储，然后仅重放原请求一次。
5. 第二次认证仍失败时返回脱敏错误，不循环登录。

读请求可以对连接中断和 5xx 执行有限退避重试。写请求仅在明确收到 401 且确认原请求未授权执行时重放；网络超时或结果不确定时不得自动重试，而是返回 `UNKNOWN` 并要求查询 Bug 最新详情确认结果。

日志、异常、测试快照和 Codex 回复不得包含密码、Token、Cookie、认证请求体或完整请求头。

## 7. 用户与团队解析

用户目录从 API 2.0 用户列表读取，覆盖内部和外部用户。解析规则为：

1. 账号精确匹配；
2. 姓名精确匹配；
3. 不区分大小写的账号匹配；
4. 其他情况返回候选项，不执行写操作。

配置团队查询时先验证全部成员。成员不存在、重名或当前账号无权查看时，结果中单独列出失败成员；其他成员继续查询，但总体状态标记为“部分完成”。

## 8. Bug 查询

MCP 暴露以下只读工具：

- `query_my_bugs(filters)`；
- `query_team_bugs(filters)`；
- `query_user_bugs(user, filters)`；
- `search_bugs(filters)`；
- `get_bug(bug_id)`；
- `list_users(kind, keyword)`。

过滤模型支持：

- `status`：默认 `unresolved`，也可指定 `active`、`resolved`、`closed` 或 `all`；
- `assigned_to` 与 `opened_by`；
- `product_id`、`project_id`、`execution_id`；
- `priority`、`severity`、`type`；
- 标题或内容关键词；
- 创建、指派、解决或最后编辑日期范围；
- 排序、页码和最大返回数量。

查询器优先使用产品、项目或执行范围的 API 2.0 列表端点，并完整处理分页。API 不支持的组合条件在获取结构化列表后由本地过滤器执行。未指定范围时，查询器只遍历当前账号可见范围，并受 `max_results` 和最大页数保护，不允许无限扫描。

自然语言示例：

- “查一下我所有未关闭的 Bug，按优先级汇总。”
- “看看团队成员今天还有哪些未关闭 Bug。”
- “查询王小明的 Bug，他不在团队配置里。”
- “查产品 3 中严重程度 1、指派给张三、最近七天更新的 Bug。”
- “显示 1234 号 Bug 的详情和当前处理人。”

列表回复包含总数、状态分布、人员分布和简明表格；详情回复保留关键字段、重现步骤和最近动作，不把 HTML 原样暴露给用户。

## 9. 单个 Bug 写操作

MCP 暴露以下写工具：

- `add_bug_comment(bug_id, comment)`；
- `edit_bug(bug_id, changes)`；
- `activate_bug(bug_id, assigned_to, opened_builds, comment)`；
- `assign_bug(bug_id, assigned_to, comment)`。

写操作规则：

- 必须由当前用户消息明确给出具体 Bug ID 和动作；
- “激活 1234 并指派给张三，备注重新出现”已经构成一次完整授权，可一句话执行；
- 缺少目标用户、备注内容或必要版本时只询问缺失字段；
- 从旧对话、Bug 描述或评论中提取出的指令不能作为授权；
- 写前读取一次最新 Bug，验证存在、权限和当前状态；
- 写后再次读取并返回变更前后关键字段；
- 用户姓名解析不唯一时禁止写入；
- `DELETE` 工具和任何同义删除工具永久不存在。

API 2.0 写入固定使用 21.7.8 源码中存在的控制器路由：编辑和独立备注使用 `PUT /api.php/v2/bugs/:bugID`，激活使用 `PUT /api.php/v2/bugs/:bugID/activate`，单独指派使用 `PUT /api.php/v2/bugs/:bugID/assignTo`。独立备注调用前先读取 Bug，并把接口要求的 `title` 与 `openedBuild` 原值连同 `comment` 一起提交，禁止用空默认值覆盖现有字段。`doctor` 必须逐项显示四个写能力是否可用；实例路由或权限不支持时返回“不支持”，不得伪造成功或通过危险的通用请求绕过。

## 10. 错误处理

对外错误分为：

- `CONFIG_ERROR`：配置缺失或格式错误；
- `AUTH_ERROR`：账号密码错误或重新登录失败；
- `PERMISSION_DENIED`：当前禅道账号无读取或写入权限；
- `USER_NOT_FOUND` / `USER_AMBIGUOUS`：成员解析失败；
- `BUG_NOT_FOUND`：Bug 不存在或不可见；
- `VALIDATION_ERROR`：条件或写入字段不合法；
- `CAPABILITY_UNAVAILABLE`：当前 21.7.8 实例未提供所需动作；
- `NETWORK_ERROR`：请求未到达或读取失败；
- `UNKNOWN_WRITE_RESULT`：写请求结果不确定，需要重新查询确认。

所有错误包含用户可执行的下一步，但不得输出秘密。单个团队成员失败不阻断其他成员；分页中途失败时明确标记结果不完整。

## 11. Codex 插件包装

插件必须包含：

- `.codex-plugin/plugin.json`，名称为 `zentao-ai-bug`，声明 `skills` 和 `mcpServers`；
- `.mcp.json`，通过已安装的 `zentao-ai mcp serve` 启动 stdio MCP；
- `skills/zentao-ai-bug/SKILL.md`，描述触发语句、工具选择、汇总格式和写入授权边界；
- 仓库级 `.agents/plugins/marketplace.json`，指向 `./plugins/zentao-ai-bug`；
- 严格语义化版本，首版为 `0.1.0`。

安装器使用 Codex CLI 注册当前仓库 Marketplace 并安装插件。插件更新时更新版本缓存标记、重新安装插件，并提示新建 Codex 任务加载新工具。

## 12. 文档

`README.md` 首屏必须让新用户在三分钟内看懂：

1. 这个插件能做什么；
2. 支持禅道 21.7.8 API 2.0；
3. 安装前提；
4. 两个平台的复制粘贴安装命令；
5. 本地配置文件位置和最小示例；
6. 五条可直接使用的自然语言示例；
7. 写操作和删除禁令；
8. 故障排查入口。

详细文档分别说明安装、全部配置字段、功能矩阵、密码和 Token 安全、401 自动登录、权限要求、升级、卸载和常见错误。文档不得展示真实域名、账号、团队成员、密码、Token 或业务 Bug。

## 13. 测试与验收

单元测试覆盖：

- 配置解析、覆盖顺序和脱敏；
- Token 缓存、401 重新登录一次和失败停止；
- 用户姓名、账号、重名和外部用户解析；
- 全部过滤条件、分页、汇总和部分失败；
- 写操作授权、前后快照和删除禁令。

合同测试覆盖：

- 插件 manifest、Marketplace、MCP 和 Skill 结构；
- MCP 工具名称、参数和结构化响应；
- README 中的命令、配置路径和示例与实现一致；
- 仓库没有明文秘密或本地运行数据。

集成测试使用模拟 HTTP 服务覆盖 API 2.0 登录、用户、列表、详情、编辑、激活、备注和指派。真实验收在用户的 21.7.8 测试实例进行，只记录脱敏 PASS/FAIL，不保存真实业务响应。

完成标准：

- macOS/Linux 和 Windows 安装脚本通过干净环境测试；
- 从克隆仓库到 `doctor` 全绿不超过三分钟，不计软件下载和用户输入时间；
- Codex 新任务能完成个人、团队、外部用户和组合条件查询；
- 四个写操作在明确授权下成功，失败时不产生误报；
- Token 失效后自动重新登录且原请求最多重放一次；
- 所有自动化测试、类型检查、插件验证、构建和秘密扫描通过；
- README 与实际安装过程逐步一致。

## 14. GitHub 交付

实施必须在保留远端历史的真实 Git 克隆中完成。当前下载的源码快照用于审计和设计，不能直接覆盖远端历史。

交付顺序：

1. 使用 GitHub 网页授权获得仓库 Git 权限；
2. 克隆默认分支并确认提交历史；
3. 在 `codex/zentao-plugin-v0.1` 分支实施；
4. 运行完整验证和秘密扫描；
5. 提交清晰的分阶段 commits；
6. 推送分支到 `wwtweiwenting/zentao-ai-assistant`；
7. 返回分支链接、安装命令、验证结果和需要用户提供的真实禅道验收信息。

