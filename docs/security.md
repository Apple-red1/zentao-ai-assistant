# 安全模型

## 秘密与认证

- `.env` 保存本地连接信息并被 Git 忽略；`.env.example` 不包含真实秘密。
- Token 通过 API v2 登录取得，仅存在当前 Python 进程内存中。
- 输出层递归脱敏 password/token/Authorization/Cookie 类字段，包括 `ZENTAO_PASSWORD`、`resetToken` 等变体。
- 不持久化 Token，不把 Token 写回 `.env`。

## 写入与结果不确定

`POST`、`PUT`、`DELETE` 不自动重试。服务器明确返回失败时映射为 `API_ERROR`；请求确定未送达时返回 `NETWORK_ERROR`；请求可能已经执行但客户端无法确认结果时返回 `UNKNOWN_WRITE_RESULT`。

收到 `UNKNOWN_WRITE_RESULT` 后，当前命令立即结束，不自动 GET、不执行第二个业务动作，也不自动重放原写请求。

## 读取重试

只有 GET 读取允许有限重试：临时网络故障或 `502/503/504` 最多额外重试 2 次；`400/401/403/404` 不重试。当前退避基线为约 `0.2s`、`0.5s`。

## 删除

删除属于 R3。能力面保留官方 delete endpoint，但 CLI 在未提供 `--yes` 时必须在发送业务 HTTP 前拒绝执行；Skill 只有在当前用户请求明确表达删除具体资源时才允许使用该参数。
