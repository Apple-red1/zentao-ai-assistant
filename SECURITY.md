# Security

详细安全合同见 [`docs/security.md`](docs/security.md)。

真实 `.env`、Home config、密码、Token、Cookie 与认证 Header 不得提交或写入日志。
运行时不扫描业务 cwd 的 `.env`，也不混用 project/user 两个配置文件；只按当前
合同选择 `ZENTAO_CONFIG_FILE`、代码根 `.env` 或
`~/.zentao-ai-assistant/config.env` 其中一个来源。

Token 不写回配置文件；project scope 短期 cache 为 `.tmp/zentao/auth/`，user
scope 短期 cache 为 `~/.zentao-ai-assistant/cache/auth/`，缓存不包含密码并受
`0700` 目录、`0600` 文件和 TTL 约束。Claude/Codex Plugin cache 只视作可替换
代码目录，不保存持久 secret；资源和高层 cache-data 也按 scope 写入 trusted
temp root，保持同源、符号链接、路径逃逸和脱敏安全规则。

明确 401 仍只允许认证层清理旧 Token、重新登录并重放被拒绝请求一次；写请求
不确定结果仍为 `UNKNOWN_WRITE_RESULT`，不得自动重放。
