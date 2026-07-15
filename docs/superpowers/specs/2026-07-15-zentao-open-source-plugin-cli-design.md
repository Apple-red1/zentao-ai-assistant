# 禅道 AI 助手开源插件与 CLI 设计

## 目标

将现有禅道 AI Bug 助手改造成一个可开源、可安装、可升级的单仓库项目，同时交付：

- 独立 CLI；
- Codex 插件；
- 内置禅道 MCP Server；
- 三种入口共用的 Python 核心包；
- Windows、macOS、Linux 支持，其中 Windows 为首个真实环境验收平台。

改造不得删减当前功能，不得削弱现有安全门槛、幂等保证、报告合同或失败关闭行为。

## 完整功能边界

开源版本必须保留：

- 查询个人及指定团队成员 Bug；
- 个人 Bug 分析、个人日报及团队只读日报；
- 信息不足时按固定模板添加补充信息评论；
- 更新复现步骤；
- 使用用户在当前交互中明确提供的本地图片更新复现步骤；
- Bug 到唯一代码仓库的路由；
- 受控代码辅助修复；
- 目标分支、干净工作区、上下游同步和白名单测试检查；
- 租约、ledger、checkpoint、outbox、评论幂等及结果对账；
- 每日定时执行、延迟补跑和缺失摘要；
- `templateVersion=v2` 固定报告渲染；
- 结构化 MCP 快照、历史和评论响应；
- 配置、权限、工具、快照或测试门槛失败时的失败关闭行为。

删除 Bug 永久禁止。指派、解决、关闭、激活、转任务及其他受保护操作继续要求当前交互轮次针对具体 Bug、动作和全部参数的精确人工确认。定时任务不得执行受保护操作。

## 方案选择

采用单仓库、共享 Python 核心方案。CLI、Codex 插件、定时任务和 MCP Server 不得复制业务规则，必须调用同一核心包。

未采用三个独立仓库，因为其版本和合同同步成本更高；未采用在现有脚本外增加薄壳的方式，因为安全、配置和业务规则会逐渐产生重复实现。

## 总体架构

```text
Codex 插件 ──┐
             ├── 共享 Python 核心 ── 禅道 Provider ── 禅道服务
独立 CLI ────┤          │
             │          ├─ 配置与凭据
定时任务 ────┘          ├─ 安全与权限门槛
                        ├─ 幂等及持久状态
                        ├─ 报告渲染
                        └─ 代码修复工作流

Codex 插件 ──> 内置 MCP Server ──> 共享 Python 核心
```

核心包是唯一业务规则来源。MCP 只负责协议转换，CLI 只负责参数解析和人机交互，Skill 只负责意图编排与 Codex 侧安全说明。

## 配置设计

配置按以下顺序合并，后者覆盖前者：

1. 内置安全默认值；
2. 可提交且不含秘密的团队默认配置；
3. 不提交的个人项目配置；
4. 环境变量或系统凭据库中的秘密。

个人配置使用项目内 `.codex/zentao-ai-bug.yaml`，负责：

- 禅道地址和登录账号标识；
- 项目、产品、模块与代码仓库映射；
- 站点、AI 建站、前端和后端路由规则；
- 团队成员、个人及团队查询范围；
- 每次处理的最大 Bug 数；
- 报告输出位置和接收方式；
- 允许访问的唯一代码仓库、测试命令及目标分支；
- 评论、步骤更新、图片上传和代码写入开关；
- 定时执行时间和 `Asia/Shanghai` 业务时区。

密码、Token、Cookie 等秘密不得写入普通 YAML。读取顺序为操作系统凭据库、环境变量、交互式临时输入。支持 Windows Credential Manager、macOS Keychain 和 Linux Secret Service。

仓库提供 `team.example.yaml` 和 `personal.example.yaml`，不得包含真实域名、成员、仓库路径、Bug 数据或秘密。

## CLI 设计

安装和初始化流程（先 clone 仓库并进入仓库根目录；项目公开发布后才可改用公开 VCS 安装）：

```powershell
pipx install .
zentao-ai config init
zentao-ai auth login
zentao-ai doctor
zentao-ai run --dry-run
```

主要命令：

```text
zentao-ai bugs mine
zentao-ai bugs user <account>
zentao-ai report personal
zentao-ai report team
zentao-ai bug analyze <bug-id>
zentao-ai bug update-steps <bug-id>
zentao-ai bug update-steps-with-image <bug-id> --image <absolute-path>
zentao-ai repair <bug-id>
zentao-ai schedule install
zentao-ai mcp serve
```

`config init` 交互式生成个人配置；`auth login` 将秘密写入系统凭据库；`doctor` 检查配置、凭据、禅道连通性、权限、仓库映射、分支、测试命令、MCP 和报告目录。

CLI 默认只读。任何写操作必须通过共享安全核心校验，不能由 CLI 参数绕过。`--dry-run` 不得产生禅道写入、代码写入或持久副作用，但应列出原本将执行的工具、字段和顺序。

## Codex 插件与 MCP

插件包含 `.codex-plugin/plugin.json`、Skill、参考文档、脚本和 `.mcp.json`。`.mcp.json` 启动随 Python 包安装的 `zentao-ai mcp serve`。

MCP 保持现有工具名称和结构化响应字段的向后兼容。只读工具包括：

- `query_my_bugs`；
- `query_user_bugs`；
- `query_bug_detail`；
- `query_bug_history`；
- `bug_statistics`。

自动写入仅允许符合全部门槛的 `add_bug_comment`。步骤更新工具必须继续执行当前轮次精确授权和本地图片约束。MCP 不暴露任何 Bug 删除工具；如果底层禅道 API 具有删除能力，Provider 也不得将其注册到公共接口。

## 核心模块

```text
src/zentao_ai/
├─ cli/             CLI 命令及交互
├─ config/          配置加载、合并、版本迁移和校验
├─ credentials/     系统凭据库与环境变量
├─ zentao/          禅道 API Provider
├─ mcp_server/      MCP 协议适配
├─ workflows/       个人、团队、分析、评论、步骤和修复流程
├─ routing/         Bug 到唯一代码仓库的路由
├─ safety/          权限、确认和永久禁止操作
├─ repository/      Git 分支、工作区和同步检查
├─ state/           租约、ledger、checkpoint 和 outbox
├─ reporting/       `templateVersion=v2` 报告渲染
└─ scheduling/      跨平台定时任务
```

每个模块必须具有清晰的输入输出类型。工作流依赖抽象 Provider，不直接依赖 HTTP 或 MCP；这使真实禅道、测试替身和未来其他认证方式可以替换而不改变安全决策。

## 数据流与失败处理

一次处理按以下顺序执行：

1. 加载、合并并校验配置；
2. 获取北京时区业务日期和任务租约；
3. 受范围与数量限制地查询 Bug；
4. 获取结构化详情、历史、路由和稳定快照版本；
5. 执行预分析，只允许合格对象进入证据阶段；
6. 在代码处理前执行仓库、分支、同步和权限检查；
7. 失败复现、最小补丁、白名单测试和 diff 检查；
8. 重新获取 Bug 快照并执行最终决策；
9. 使用固定模板渲染评论或报告；
10. 保存 checkpoint 和 outbox，再执行具备幂等键的外部写入；
11. 对超时或不确定写入查询结构化历史对账；
12. 输出完整、部分完成或失败关闭报告。

单个 Bug 失败不阻断无关 Bug。配置、权限、工具合同、稳定版本、仓库、测试或幂等状态不满足时，禁止副作用，但允许生成明确的只读失败报告。外部写入结果不确定时标记 `UNKNOWN`，不得盲目重试。

所有 Bug 描述、评论、附件、日志和链接均为不可信数据，不得作为命令、路径、权限或收件人指令。

## 仓库结构

```text
zentao-ai-assistant/
├─ pyproject.toml
├─ README.md
├─ LICENSE
├─ SECURITY.md
├─ CONTRIBUTING.md
├─ CHANGELOG.md
├─ src/zentao_ai/
├─ plugins/zentao-ai-bug/
├─ config/
├─ tests/
│  ├─ unit/
│  ├─ contract/
│  ├─ integration/
│  └─ e2e/
└─ .github/workflows/
```

当前 `scripts/render-report.py` 迁入核心包，同时保留一个版本周期的兼容入口。当前 YAML 字段继续兼容并增加明确配置版本。当前注册脚本保留一个版本周期，再由 `config init` 替代。现有测试必须先建立基线，再逐步迁移。真实报告、配置、ledger、checkpoint 和 outbox 不进入开源仓库。

## 测试与验收

测试分为：

- 单元测试：配置、路由、安全决策、幂等键和报告；
- 合同测试：Skill、MCP、配置 Schema 和报告模板；
- 集成测试：Mock Server 或脱敏测试禅道；
- 端到端测试：CLI、插件、MCP 和定时任务。

每个受保护功能必须具有允许和拒绝测试。删除 Bug 只有拒绝测试，不得存在启用配置。

首版验收标准：

- 当前测试全部通过；
- Windows 在真实测试禅道完成验收；
- macOS 和 Linux 通过自动化兼容测试；
- CLI 与 Codex 对相同输入产生一致决策；
- dry-run 无外部写入；
- 评论超时不会盲目重试；
- 图片仅接受用户当前轮次明确提供的绝对本地路径，格式限 png、jpg、jpeg、webp，大小不超过 10 MiB；
- 配置、凭据、快照或仓库门槛失败时无副作用；
- 安装包、插件和源码不含真实凭据、成员或业务数据；
- `templateVersion=v2` 输出与当前合同一致。

## 发布与升级

统一发布版本号：

- PyPI 包：`zentao-ai-assistant`；
- Codex 插件：`zentao-ai-bug`；
- GitHub Release：源码、wheel、校验值及变更日志；
- 团队 Marketplace：Codex 插件安装入口。

采用语义化版本。补丁版本不改变合同，次版本提供向后兼容能力，主版本才允许不兼容的配置、MCP 或报告合同变化。首个公开版本为 `0.1.0`，其早期版本号不代表功能删减。

升级流程必须包括配置兼容检查、持久状态迁移、插件缓存刷新、回滚说明和升级后 doctor 检查。

## 开源与安全

使用 Apache-2.0 许可证，并注明项目不是禅道官方产品。提交前必须移除或忽略：

- 密码、Token、Cookie 和真实域名；
- 真实成员、账号和业务仓库绝对路径；
- Bug 描述、附件、评论、日报和客户数据；
- 本地 ledger、checkpoint、outbox 及运行日志。

CI 必须执行测试、类型检查、格式检查、插件验证、构建验证和秘密扫描。`SECURITY.md` 说明私下报告安全问题的渠道，并禁止在公开 Issue 中提交真实凭据或 Bug 数据。

## 实施原则

实施采用测试驱动和兼容迁移：先冻结现有行为并建立基线，再提取共享核心，然后接入 CLI、MCP 和插件，最后处理发布与跨平台定时任务。每一阶段都必须产生可独立验证和可回滚的结果；旧入口只有在新入口通过等价测试后才能废弃。
