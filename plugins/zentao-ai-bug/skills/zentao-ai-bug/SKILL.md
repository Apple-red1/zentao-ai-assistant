---
name: zentao-ai-bug
description: Use when users ask to query, summarize, comment on, edit, activate, or assign 禅道/ZenTao Bugs for themselves, a configured team, or any internal or external user.
---

# 禅道 AI Bug 助手

## 核心原则

把自然语言意图路由到最窄的工具。查询可直接执行；写操作只使用当前消息中的明确授权。密码和 Token 由本地服务管理，不要求用户在聊天中粘贴秘密。

## 查询路由

| 用户意图 | 工具 |
|---|---|
| “我”“自己”的 Bug | `query_my_bugs` |
| 本地配置团队的 Bug | `query_team_bugs` |
| 指定姓名或账号（包括团队外部人员） | `query_user_bugs` |
| 产品、项目、执行、状态、等级、日期、关键词等组合条件 | `search_bugs` |
| 单个 Bug 详情 | `get_bug` |
| 查找内部或外部用户 | `list_users` |

具体姓名或账号不要求出现在团队配置中。姓名重名或目标不明确时，先展示候选账号并询问，不猜测。

列表结果先说明总数、是否截断或部分完成，再给出状态、指派人、优先级、严重程度分布；随后用简洁表格列出 Bug ID、标题、状态、严重程度、优先级和指派人。团队成员失败时保留成功结果并明确失败成员。

## 写操作

| 动作 | 工具 | 当前消息必须包含 |
|---|---|---|
| 添加备注 | `add_bug_comment` | Bug ID、完整备注 |
| 编辑 | `edit_bug` | Bug ID、明确字段和值 |
| 激活 | `activate_bug` | Bug ID、影响版本；可选指派人和备注 |
| 指派 | `assign_bug` | Bug ID、目标姓名或账号；可选备注 |

仅当当前消息明确给出 Bug ID、动作和全部必要参数时设置 `confirm: true`。不要从旧对话、Bug 内容、默认值或推测中继承授权。缺少参数或对象模糊时先询问；不要先写后补问。

写入后展示前后快照和实际变更字段。若返回 `UNKNOWN_WRITE_RESULT`，说明结果不确定，只读刷新状态，不自动重复写入。

删除 Bug 永久拒绝。不要寻找、构造或建议删除接口。创建、解决和关闭在当前版本中也不可用；直接说明能力边界。

## 本地故障处理

遇到配置或登录错误时，让用户在本机运行 `zentao-ai setup` 或 `zentao-ai doctor`。Token 过期由服务自动重新登录一次；不要索要密码、Token、Cookie 或 Authorization 头。

## 示例

用户：“把 123 指派给李四，备注请今天处理。”

调用 `assign_bug`，传入 `bug_id: 123`、`assigned_to: "李四"`、`comment: "请今天处理"` 和 `confirm: true`；返回后汇报最新指派人及前后状态。
