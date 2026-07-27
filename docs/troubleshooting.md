# 排错指南

先运行：

```bash
zentao-ai doctor
```

## 检查项

| 检查项 | 常见原因 | 处理 |
|---|---|---|
| `CONFIG` | 配置不存在、YAML 格式错误或出现禁止的秘密字段。 | 运行 `zentao-ai setup`；自定义路径时设置 `ZENTAO_CONFIG`。 |
| `CREDENTIALS` | 系统凭据库没有当前站点与账号的密码。 | 再次运行 `zentao-ai setup --update`。 |
| `LOGIN` | 地址、账号、密码不正确，或站点不可达。 | 先用浏览器验证登录，再更新本地配置；不要把秘密发到聊天。 |
| `API_V2` | 禅道版本、路由或反向代理未开放 API v2。 | 确认版本为 21.7.8，并检查 `/api.php/v2` 路由。 |
| `TEAM_MEMBERS` | 配置账号不存在，或姓名与账号不对应。 | 使用实际禅道账号更新 `team.members`。 |
| `QUERY_MY_BUGS` | 账号没有产品/Bug读取权限，或 API 分页响应异常。 | 给账号授予最小读取权限，再重试。 |
| `EDIT` / `COMMENT` / `ACTIVATE` / `ASSIGN` | 本地 `writes.enabled` 关闭，或账号缺少写权限。 | 确认本地开关与禅道权限；doctor 不会执行真实写入。 |
| `MCP` | Python 包、插件或命令入口未正确安装。 | 重新运行安装器，随后重启 Codex 或新建任务。 |

## 常见错误

### `AUTH_ERROR`

重新运行 `zentao-ai setup --update`，然后运行 doctor。Token 失效本应自动重新登录；持续失败通常是密码、账号或权限变化。

### `USER_AMBIGUOUS`

姓名对应多个账号。改用准确账号查询或指派。

### `UNKNOWN_WRITE_RESULT`

不要重复原写命令。先说“查看 Bug 123 最新状态”，确认实际结果后再决定下一步。

### Codex 看不到插件

```bash
codex plugin list
codex plugin add zentao-ai-bug@zentao-ai-assistant
```

确认仓库 Marketplace 已注册，然后重启 Codex 或新建任务。

### `zentao-ai` 不在 PATH

重开终端，让 pipx 的 PATH 更新生效；再运行 `python3 -m pipx ensurepath`。Windows 使用 `py -3.11 -m pipx ensurepath`。
