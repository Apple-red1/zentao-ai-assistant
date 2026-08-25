# 安全模型

## 秘密与认证

- `.env` 保存本地连接信息并被 Git 忽略；`.env.example` 不包含真实秘密。
- Token 通过 API v2 登录取得，仅存在当前 Python 进程内存中。
- 输出层递归脱敏 password/token/Authorization/Cookie 类字段，包括 `ZENTAO_PASSWORD`、`resetToken` 等变体。
- 不持久化 Token，不把 Token 写回 `.env`。
- `setup` 通过同目录临时文件原子写入 `.env`：POSIX 创建即验证 `0600`，写入 flush/fsync 后才 replace；安全失败不吞错、不破坏旧配置，也不把秘密放进错误详情。

## 对象资源下载

- `resource fetch` 不接受任意 URL，只能从当前 ZenTao 对象详情的附件区和富文本发现资源地址。
- HTTP/HTTPS 资源必须与 `ZENTAO_BASE_URL` 同源；URL 中的用户凭据被拒绝。
- 重定向由客户端逐跳处理，每一跳重新执行同源校验；跨源重定向在发送下一跳请求前拒绝，因此 Token 不会被带到外部站点。
- HTTP 文件流式写入项目根目录 `.tmp/zentao-resources/`，下载中的 `.part` 文件失败后清理。
- 服务端文件名和 URL 文件名在落盘前去除目录成分和控制字符，最终路径始终由项目 `.tmp/` 目录重新构造，避免附件名路径穿越。
- `.tmp/` 被 Git 忽略；资源默认保留，由调用者显式清理，不做隐式删除。

## 写入与结果不确定

`POST`、`PUT`、`DELETE` 不自动重试。服务器明确返回失败时映射为 `API_ERROR`；请求确定未送达时返回 `NETWORK_ERROR`；请求可能已经执行但客户端无法确认结果时返回 `UNKNOWN_WRITE_RESULT`。

收到 `UNKNOWN_WRITE_RESULT` 后，当前命令立即结束，不自动 GET、不执行第二个业务动作，也不自动重放原写请求。

## 读取重试

普通 GET 和资源二进制 GET 允许有限重试：临时网络故障或 `502/503/504` 最多额外重试 2 次；普通业务 `400/401/403/404` 不重试。当前退避基线为约 `0.2s`、`0.5s`。

## 删除

删除属于 R3。能力面保留官方 delete endpoint，但 CLI 在未提供 `--yes` 时必须在发送业务 HTTP 前拒绝执行；Skill 只有在当前用户请求明确表达删除具体资源时才允许使用该参数。
