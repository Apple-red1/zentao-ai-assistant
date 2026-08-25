# Security

详细安全合同见 [`docs/security.md`](docs/security.md)。

真实 `.env`、密码、Token、Cookie 与认证 Header 不得提交或写入日志。Token 不写回 `.env`；允许按当前安全合同短期缓存在 Git ignored 的 `.tmp/zentao/auth/`，缓存不包含密码并受本地权限/TTL 约束。
