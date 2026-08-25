---
name: zentao
description: Use when users ask to read or explicitly change ZenTao through the official API v2 capability surface, including bugs, stories, tasks, products, projects, tests, feedback, tickets, files, users, and related lifecycle operations.
---

# 禅道（zentao）

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

Token 登录由内部 `token.login` 认证适配自动完成，不建立业务 `token` 命令域；`doctor` 可验证配置和登录。

## 风险与授权

- **R0 Read**：list/view，可直接执行。
- **R1 Normal Write**：create/edit/upload/change；只有当前用户明确要求该写操作时执行。
- **R2 Lifecycle**：resolve/close/activate/start/finish；只有当前用户明确要求对应生命周期动作时执行。
- **R3 Destructive**：delete；必须同时满足“用户当前请求明确删除具体资源”以及 CLI 带 `--yes`。模糊的“处理/清理”不能推断为删除授权。

一条 CLI 命令只执行一个明确业务 endpoint。禁止写后自动 GET、自动第二次写或写请求自动重试。收到 `UNKNOWN_WRITE_RESULT` 时不要直接重放原写操作；在任何后续写入前，先通过显式的只读 `view/list` 命令确认当前状态。

## 输出与错误

- 默认输出面向终端阅读；`--json` 输出机器结果。
- `--json` 成功：stdout 只包含领域 JSON；DELETE 等空响应返回最小 `{"status":"success"}`（已知 ID 时包含 `id`）。
- `--json` 失败：stdout 为空，stderr 输出 `{"error":{"code","message","details"}}`。
- exit `0` 成功；`1` 运行/API/认证/网络错误；`2` 参数/用法错误；`130` Ctrl+C。
- 密码、Token、认证 Header 永远不能进入输出。

## 配置

项目根目录 `.env`：`ZENTAO_BASE_URL`、`ZENTAO_ACCOUNT`、`ZENTAO_PASSWORD`。Token 只保存在当前 Python 进程内存中，不持久化。
