---
name: zentao
description: Use when users ask to read or explicitly change ZenTao through the official API v2 capability surface, or fetch object-associated attachment/rich-text resource files for further analysis.
---

# 禅道（zentao）

仓库当前合同索引见 [`docs/current-contract.md`](../../docs/current-contract.md)。本文件
负责 Skill 的用户调用、安全授权和输出语义；endpoint 机器合同及真实兼容性按该索引
分别读取，不以历史 `RULES.md` 为依据。

## 调用入口

唯一执行入口：

```bash
python skills/zentao/scripts/zentao.py <resource> <action> [scope] [parameters] --json
```

先根据用户意图定位资源并读取对应 reference；参数不确定时执行对应命令的 `--help`。`references/api-v2/endpoints.json` 只用于覆盖审计，不作为运行时动态路由表。

## 资源导航

- `bug` → `references/api-v2/bugs.md`
- `build` → `references/api-v2/builds.md`
- `epic` → `references/api-v2/epics.md`
- `execution` → `references/api-v2/executions.md`
- `feedback` → `references/api-v2/feedbacks.md`
- `file` → `references/api-v2/files.md`
- `resource` → `references/resources.md`（对象关联资源获取，Skill 增强能力）
- `product` → `references/api-v2/products.md`
- `product-plan` → `references/api-v2/product-plans.md`
- `program` → `references/api-v2/programs.md`
- `project` → `references/api-v2/projects.md`
- `release` → `references/api-v2/releases.md`
- `requirement` → `references/api-v2/requirements.md`
- `story` → `references/api-v2/stories.md`
- `system` → `references/api-v2/systems.md`
- `task` → `references/api-v2/tasks.md`
- `test-case` → `references/api-v2/test-cases.md`
- `test-task` → `references/api-v2/test-tasks.md`
- `ticket` → `references/api-v2/tickets.md`
- `user` → `references/api-v2/users.md`

Token 登录由内部 `token.login` 认证适配自动完成，不建立业务 `token` 命令域；`doctor` 可验证配置和登录。仓库内其他高层 Skill 通过 `references/programmatic.md` 说明的 public facade 复用该基础能力。

## 配置与运行 scope

直接 clone 使用 project scope：`setup` 或 `setup --scope project`；Plugin 或
用户级配置使用 `setup --scope user`。

`setup` 通过交互式提示读取密码，不接受 `--password`；写入后必须显式执行
`doctor --json` 验证配置和 API v2 登录。命令输出、错误和文档示例都不显示
密码或 Token。

配置文件严格按 `ZENTAO_CONFIG_FILE` → 仓库根目录 `.env`（存在时）→
`~/.zentao-ai-assistant/config.env` 选择一个文件；不跨文件补字段，环境变量
覆盖所选文件同名键。显式指定的配置文件不存在时直接报错；显式指定非仓库根目录
配置时，连接使用该文件，Token/cache/resource 等运行数据使用 user scope。

运行数据随 scope 隔离：

```text
project: <repo>/.tmp/zentao/auth/
         <repo>/.tmp/zentao-resources/
         <repo>/.tmp/zentao/<skill>/
user:    ~/.zentao-ai-assistant/cache/auth/
         ~/.zentao-ai-assistant/tmp/zentao-resources/
         ~/.zentao-ai-assistant/tmp/zentao/<skill>/
```

Token cache 只保存短期 Token，不保存密码；临时资源和高层聚合材料不是长期
事实源。

## 风险与授权

- **R0 Read**：list/view，可直接执行。
- **R1 Normal Write**：create/edit/upload/change；只有当前用户明确要求该写操作时执行。
- **R2 Lifecycle**：resolve/close/activate/start/finish；只有当前用户明确要求对应生命周期动作时执行。
- **R3 Destructive**：delete；必须同时满足“用户当前请求明确删除具体资源”以及 CLI 带 `--yes`。模糊的“处理/清理”不能推断为删除授权。

官方 API 资源命令一条 CLI 命令只执行一个明确业务 endpoint。`resource fetch` 是已单独冻结的只读组合获取能力，可执行一次对象详情读取和零到多个同源资源 GET。禁止写后自动 GET、自动第二次写或写请求自动重试。收到 `UNKNOWN_WRITE_RESULT` 时不要直接重放原写操作；在任何后续写入前，先通过显式的只读 `view/list` 命令确认当前状态。

## 对象关联资源

`view` 只读取对象详情，不自动下载附件。用户明确要求获取、查看或分析对象资源时，先用对应 `view` 获取文本事实，再执行 `resource fetch --object-type <type> --object-id <id> --json`。

`resource fetch` 只从对象附件区和富文本发现资源，尝试获取全部文件并保存到
当前 runtime scope 的资源临时目录；不接受任意 URL。至少一个资源成功时保留
成功结果并报告 `partial_failures`，全部失败才返回 `RESOURCE_FETCH_FAILED`。
下载后的图片/文档/日志等由宿主按可用能力继续理解。

## 输出与错误

- 对象链接先读取[对象 Web URL 证据合同](references/web-urls.md)；不得仅凭 ID、base URL 或历史示例拼接链接。无可靠证据时返回对象 ID 及“页面 URL：当前能力无法可靠生成/尚未验证”；API 成功不等于页面已验证，CLI 无通用页面生成/验证能力。
- 默认输出面向终端阅读；`--json` 输出机器结果。
- `--json` 成功：stdout 只包含领域 JSON；DELETE 等空响应返回最小 `{"status":"success"}`（已知 ID 时包含 `id`）。
- `--json` 失败：stdout 为空，stderr 输出 `{"error":{"code","message","details"}}`。
- exit `0` 成功；`1` 运行/API/认证/网络错误；`2` 参数/用法错误；`130` Ctrl+C。
- 密码、Token、认证 Header 永远不能进入输出。
