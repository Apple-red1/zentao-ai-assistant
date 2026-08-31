# zentao-ai-assistant

让 AI 通过 ZenTao 官方 API v2 查询项目、统计工作量、整理个人待办，并按明确授权处理 Bug。
提供 **6 个 Skills**，支持直接 Clone 使用，也提供 Claude Code / Codex 插件安装入口；
两种方式共用根目录的同一份 `skills/`。

当前行为与开发事实入口：[`docs/current-contract.md`](docs/current-contract.md)。

## 现有功能

| Skill | 能做什么 | 自然语言示例 |
|---|---|---|
| [`zentao`](skills/zentao/SKILL.md) | API 原子查询、固定同源独立评论、明确授权的写入、对象附件与富文本资源获取 | “查看 Bug 123，获取它的附件”；“给 Bug 123 添加评论” |
| [`zentao-statistics`](skills/zentao-statistics/SKILL.md) | 确定性计数、状态分布、聚合、同类范围对比 | “统计产品 1 的 Bug 状态分布” |
| [`zentao-personal`](skills/zentao-personal/SKILL.md) | 个人待办与摘要、我的团队名单、团队 Bug 与团队日报 | “把我的团队设置为张三、李四”；“查询今日团队日报” |
| [`zentao-project-management`](skills/zentao-project-management/SKILL.md) | 项目/执行进度事实、风险信号和工作量分布 | “分析项目 12 的进展和阻塞” |
| [`zentao-bug-resolver`](skills/zentao-bug-resolver/SKILL.md) | Bug 证据分析、本地修复编排，以及明确人工确认后的受控回写 | “分析 Bug 123 的根因”；“Bug 123 已解决，标记已解决” |
| [`zentao-batch-export`](skills/zentao-batch-export/SKILL.md) | 多个 ZenTao 对象的完整字段、附件/富文本资源与 ZIP 打包 | “把 bug:123、story:78 的完整资料和附件打包下载” |

基础 API 覆盖 **20 个资源、120 个 endpoint**。统计和项目分析基于实际返回数据，
不编造历史趋势、健康分或绩效结论；不完整数据会保留完整性标记。

## 安装与首次配置

### 前置条件

- Python **3.11+**，运行时和测试只用标准库，不需要 `pip install`、pipx、MCP Server 或第三方 Python 包。
- Git；使用插件时还需安装支持相应插件命令的 Claude Code 或 Codex CLI。
- 可访问的 ZenTao API v2 地址，以及有相应权限的账号和密码。

下面命令从仓库根目录执行。示例使用 `python3`；若本机使用 `python` 或 Windows 的
`py -3`，请替换命令并先确认版本满足要求。无需安装系统级 `zentao-ai` 命令。

先获取源码，再选择下面一种入口：

```bash
git clone --branch main https://github.com/Apple-red1/zentao-ai-assistant.git
cd zentao-ai-assistant
python3 --version
```

### 方式一：直接 Clone / project

适合在本仓库中使用或开发。Codex 读取 `AGENTS.md`；Claude Code 和 Gemini CLI
分别通过 `CLAUDE.md` / `GEMINI.md` 引用同一份规则，按用户目标读取对应 Skill。
不需要将六个 Skill 单独复制到宿主目录。

```bash
python3 skills/zentao/scripts/zentao.py setup --scope project
python3 skills/zentao/scripts/zentao.py doctor --json
```

`setup` 不带 `--scope` 时也默认写项目根目录 `.env`。配置完成后，在仓库中开启
Codex、Claude Code 或 Gemini CLI 会话，即可用上表中的自然语言描述任务。

### 方式二：Claude Code 插件 / user

从干净的 Clone 安装，不在安装源目录放真实 `.env`、Token 或 `.tmp` 数据。
若已有带项目配置的工作副本，请另建干净 Clone，避免本地安装时把秘密带入宿主缓存。

```bash
claude plugin validate .
claude plugin marketplace add .
claude plugin install zentao-ai-assistant@zentao-ai-assistant
```

首次连接配置写入用户目录：

```bash
python3 skills/zentao/scripts/zentao.py setup --scope user
python3 skills/zentao/scripts/zentao.py doctor --json
```

如宿主提示重载，执行 `/reload-plugins`，再开启新会话确认六个 Skill 可用。
仅做本地开发加载时可使用 `claude --plugin-dir .`，不必再执行 marketplace 安装。
宿主命令参考 [Claude Code 官方安装说明](https://code.claude.com/docs/en/plugin-marketplaces)。

### 方式三：Codex 插件 / user

同样从不含真实配置与临时数据的干净 Clone 执行：

```bash
codex plugin marketplace add .
codex plugin marketplace list
codex
```

在 Codex CLI 中输入 `/plugins`，选择 `zentao-ai-assistant` marketplace，安装
同名插件；安装后开启新会话，检查六个正式 Skill。`_shared` 只是共享实现，不是第七个 Skill。
插件浏览器与新会话要求见 [OpenAI 官方插件文档](https://learn.chatgpt.com/docs/plugins)。

首次配置在另一个终端的仓库根目录执行；若已配置 user scope，可跳过 `setup`：

```bash
python3 skills/zentao/scripts/zentao.py setup --scope user
python3 skills/zentao/scripts/zentao.py doctor --json
```

`setup --scope user` 不会把凭据写入 Clone 或宿主 Plugin cache，用户配置与运行
数据统一位于 `~/.zentao-ai-assistant/`。插件升级不要求重新复制配置。

**支持边界：** Claude Code / Codex 插件元数据和运行路径已实现，完整宿主
validate/load/install/discovery/cache 验收仍需按 [测试说明](docs/testing.md)
完成；静态检查和本地 Fake 测试不能证明插件已通过实机验收。Gemini 当前仅提供
Clone 入口；Gemini Plugin/Extension 不在 v1 范围内，Cursor/Copilot/VS Code
插件支持尚未独立验证。详见 [安装说明](docs/installation.md) 和 [功能边界](docs/features.md)。

## 配置与数据位置

`setup` 交互式读取以下三项，密码不通过命令行参数传入，也不要粘贴到对话中：

```dotenv
ZENTAO_BASE_URL=https://zentao.example.com
ZENTAO_ACCOUNT=your-account
ZENTAO_PASSWORD=your-password
```

上面是占位示例，不是真实连接信息。`setup` 只写配置；`doctor --json` 才会验证
配置并尝试真实登录 ZenTao，请在网络和账号准备好后执行。

| 数据 | project scope | user scope |
|---|---|---|
| 长期连接配置 | `<repo>/.env` | `~/.zentao-ai-assistant/config.env` |
| 短期 Token 缓存 | `<repo>/.tmp/zentao/auth/` | `~/.zentao-ai-assistant/cache/auth/` |
| 聚合材料 / 附件 | `<repo>/.tmp/` 下 | `~/.zentao-ai-assistant/tmp/` 下 |

配置文件选择顺序为 **`ZENTAO_CONFIG_FILE` → 脚本所在仓库根 `.env` → 用户配置**，
只选择一个文件，不跨文件补字段；三项同名环境变量再覆盖文件值。
`setup --scope user` 只决定写入位置，不会改变后续读取优先级；如果仓库已有 `.env`，
需要在运行命令的进程中用 `ZENTAO_CONFIG_FILE` 显式指向用户配置。
显式文件不存在会报错，不能静默回退。配置定位不依赖当前工作目录；从其他目录执行时，
请使用实际脚本绝对路径。

Token 不写回配置文件、不保存密码，默认缓存 TTL 为 8 小时；POSIX 私有目录/文件
权限目标分别为 `0700` / `0600`。不要提交 `.env`、缓存或下载资源，也不要手动把它们
放到 Claude/Codex 插件缓存。详见 [配置说明](docs/configuration.md) 和 [安全模型](docs/security.md)。

## API Skill

```bash
python3 skills/zentao/scripts/zentao.py doctor --json
python3 skills/zentao/scripts/zentao.py bug list --product 1 --json
python3 skills/zentao/scripts/zentao.py resource fetch --object-type bug --object-id 123 --json
python3 skills/zentao/scripts/zentao.py bug comment 123 --comment "已补充验证结果" --json
python3 skills/zentao/scripts/zentao.py bug comment 123 --comment "附图" --inline-image ./screenshot.png --json
```

删除属于 R3，必须有明确删除意图并传 `--yes`。

## 高层 Skill 示例

```bash
python3 skills/zentao-statistics/scripts/zentao_statistics.py summary bug --product 1 --json
python3 skills/zentao-personal/scripts/zentao_personal.py overview --json
python3 skills/zentao-project-management/scripts/zentao_project_management.py health --project 12 --json
python3 skills/zentao-batch-export/scripts/zentao_batch_export.py bug:123 story:78 task:90 --json
```

`zentao-batch-export` 只读复用基础 `view` 与 `resource fetch`，把每个对象的完整字段格式化写入 `content.md`，把附件/富文本资源归档到对象目录，并将已成功归档的正文资源引用改为 `resources/<file>`，再在当前 runtime scope 下生成动态命名的 ZIP。单项失败继续导出并完整保留到 `manifest.json` 的 `complete/failures`。

独立评论使用固定同源 Legacy Web 兼容路径，不计入官方 API endpoint；当前十种对象均支持评论、
重复普通附件和重复内嵌图片，普通附件与内嵌图片也可在同一条评论中提交。写入会在单次 POST
前后做 action snapshot/readback，结果不确定时返回 `UNKNOWN_WRITE_RESULT` 且不重放。

Bug 详情链接使用固定禅道路由直接生成，不打开浏览器：
`python3 skills/zentao/scripts/zentao.py bug web-url 3641 --json`。

六个 Skill 的聊天回复中，Bug 编号本身统一显示为可点击链接，规则见[Bug 展示说明](skills/zentao/references/bug-display.md)。原始 ID、机器 JSON、查询和写入行为不变；CLI 终端输出与 ZIP 内 `content.md` 各自遵循对应输出合同。

Bug 证据驱动流程的确定性脚本入口为：

```bash
python3 skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py select --product 1 --json
python3 skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py snapshot --bug-id 123 --json
python3 skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py compare --bug-id 123 --baseline-file <snapshot.json> --json
```

`zentao-bug-resolver` 脚本只通过 `zentao_skill.public` 只读 facade 读取 ZenTao，并由 Agent 在普通流程编排业务仓库证据、最小修改、验证和写前复查；它不是新的 API endpoint，不改变 `zentao` 的 120 endpoint 口径。普通流程的 `pending_queue` 不会自动继续；`complete=false`、`partial_failures`、`unsupported_filters` 或 `unavailable_fields` 必须保留并如实说明。需要 R2 生命周期写入时，必须在当前用户明确授权且对应分支门槛满足后回到基础 `zentao` CLI，resolver 脚本和 facade 不执行写入。

普通流程授权分为 `ANALYZE_ONLY`、`LOCAL_FIX_ALLOWED` 和 `RESOLVE_R2_ALLOWED`；结论分为
`SOLVABLE`、`UNCLEAR`、`NO_CODE_EVIDENCE`、`BLOCKED`。一次任务只处理当前 Bug，
pending 项不继承授权；模糊的“处理 Bug”最多允许本地修复，不等于 R2。只有
`SOLVABLE` 且证据、验证、diff 和写前 compare 均通过时，Agent 才能执行一次
`bug resolve` 并回读；`UNCLEAR`/`NO_CODE_EVIDENCE` 不修改业务代码。

用户明确说“3641 已解决”或目标唯一的“把刚才那个 Bug 标记已解决”时，进入
`HUMAN_ATTESTED_RESOLVE`：当前消息即人工结论和该 Bug 的 R2 授权。只做最小
`bug view`，active 时一次 `bug resolve --resolution fixed --resolved-build trunk`
并附自动生成的 `[CODEX-HUMAN-ATTESTED-RESOLUTION]` 备注，随后显式回读。
用户明确指定其它解决版本时覆盖 `trunk`；负责人按“用户显式指定 assignee > Bug creator account > BLOCKED”确定，显式人员需由完整真实用户数据唯一解析，未指定时使用当前 Bug 的创建人 account，兼容 openedByAccount/openedBy.account；`openedBy` 字符串须经完整真实用户目录做区分大小写的 account 精确校验，不按姓名或大小写回退匹配；缺失、重名、冲突或数据不完整时停止，不回退、不猜测。resolve 必须显式传 `--assignee <target-account>`，回读同时验证 `status=resolved` 且 `assignedTo=target_account`；默认不传 resolved-date，不提前追问。
此分支不检查业务源码、提交、测试、diff、附件或 patch，不运行 select/snapshot/compare。
已 resolved/closed 不重复写；当前消息列出的多个已解决 Bug 严格串行，真实阻塞即停止；
`UNKNOWN_WRITE_RESULT` 停止整个队列、绝不重试，只读回读。不自动 close/activate/delete。
“帮我解决/修复 Bug”“修复后标记已解决”“应该好了”不会直接触发人工确认写入。

详细自然语言边界见各 Skill 的 `SKILL.md`。

## 团队配置、Bug 查询与日报

由 `zentao-personal` 提供，从 **1.6.0** 开始支持，**1.7.0** 起使用阶段化团队归属。
先完成前面的禅道连接配置，
再设置自己的团队成员；安装插件本身不会自动配置团队名单。插件用户需使用包含
该功能的插件版本，仅更新源码工作区不会自动替换宿主已安装的插件副本。

### 1. 设置和维护团队

在使用本仓库 Skills 的会话中，可以直接说：

```text
查看我的团队
把我的团队设置为 alice、bob
给我的团队添加成员 张三
从我的团队移除成员 bob
```

成员可以使用禅道账号或姓名；建议优先使用账号。系统会完整读取用户目录并校验，
姓名重名、账号不存在或目录读取不完整时不会写入，需要先处理对应问题。
**你本人始终自动包含，不必重复添加**；未配置成员时，查询范围只有本人。

也可以直接运行 CLI。下面的 `alice`、`bob` 是示例账号，请替换为自己的实际成员；
按需要选择命令执行，不必依次运行所有示例。

```bash
# 查看配置成员和实际查询范围
python3 skills/zentao-personal/scripts/zentao_personal.py team-view --json

# 增量添加；重复添加同一账号不会产生重复成员
python3 skills/zentao-personal/scripts/zentao_personal.py team-add --member alice --member bob --json

# 只移除指定成员，不影响其禅道用户或 Bug
python3 skills/zentao-personal/scripts/zentao_personal.py team-remove --member bob --json

# 整体替换配置名单；不在新名单中的原成员会被移除
python3 skills/zentao-personal/scripts/zentao_personal.py team-replace --member alice --member bob --json
```

### 2. 查询团队 Bug 或日报

设置一次后，可以直接说“查询团队的 Bug”或“查询今日团队日报”；需要缩小范围时，
可以说“查询项目 1 的团队 Bug”。CLI 对应示例：

```bash
# 所有当前账号可见范围内的团队未关闭 Bug
python3 skills/zentao-personal/scripts/zentao_personal.py team-bugs --markdown

# 同一查询规则的全部明细，表格前增加团队汇总
python3 skills/zentao-personal/scripts/zentao_personal.py team-brief --markdown

# 只查询项目 1，不修改团队配置；也可改用 --product 或 --execution
python3 skills/zentao-personal/scripts/zentao_personal.py team-brief --project 1 --markdown

# 需要程序处理时使用 JSON，保留原始 ID、字段和完整性信息
python3 skills/zentao-personal/scripts/zentao_personal.py team-bugs --json
```

`--product`、`--project`、`--execution` 三选一，省略时查询所有可见范围。
“今日”指当前生成的快照，不是只查今天创建或更新的 Bug；团队日报和团队 Bug
共用同一成员范围、过滤和排序，日报不会只挑重点而省略其它符合条件的 Bug。

结果按“处理阶段 → 阶段责任人”展示：

- **需要马上行动**：`active` Bug，按当前负责人 `assignedTo` 归属。
- **待测试验证**：`resolved` 但尚未关闭的 Bug，按解决人 `resolvedBy` 归属；
  当前 `assignedTo` 作为测试负责人单独展示，即使其不属于团队也不会漏掉解决成果。
- `closed` 不进入清单。“需要马上行动”为四列，待测试验证增加第五列
  **当前测试负责人**；Bug 编号可点击，成员名下按优先级、严重程度、创建时间由早到晚排序。
- `resolvedBy` 无法解析时不猜测归属；测试负责人缺失时仍保留有效解决人的 Bug，
  显示 `—` 并通过完整性信息报告。
- 成功查询但没有 Bug 的成员显示 0；读取失败或分页不完整会明确提示，不能解释为 0。
  JSON 返回部分结果时可能仍为 exit 0，必须检查 `complete` 和 `partial_failures`。

### 3. 保存位置与清空名单

每个“禅道地址 + 登录账号”只有一个默认团队，保存在本机
`~/.zentao-ai-assistant/teams/`。同一身份跨项目、跨工作区复用；切换地址或账号后
使用另一份名单。名单不写入项目 `.env`、Git 仓库或插件缓存，也不随 Git 推送到远程。
团队配置只影响自己的查询范围，不会修改禅道用户、Bug 指派或生命周期状态。

只有确实需要清空配置成员时才执行下面的命令；清空后仍保留本人：

```bash
python3 skills/zentao-personal/scripts/zentao_personal.py team-replace --clear --json
```

完整参数、排序和异常规则见[团队合同](skills/zentao-personal/references/team.md)，
连接配置与身份隔离规则见[配置说明](docs/configuration.md#个人默认团队)。

## 测试

```bash
python tests/run_all.py
```

`zentao` API 专项仍维持 20 个资源、120 个官方 API v2 endpoint 的完整覆盖门槛；高层 Skill 的场景测试单独统计，不能把 API `120/120` 解释为整个项目的用户场景覆盖率。

高层 Skill 测试使用标准库桩和本地 FakeZenTao，Real API calls: 0；真实 ZenTao 兼容性不由这些测试冒充证明。
