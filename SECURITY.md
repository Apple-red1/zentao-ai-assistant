
# 安全

真实 `.env`、密码、Token、Cookie 与认证 Header 不得提交或写入日志。Token 只保存在当前 Python 进程内存中。

R3 删除命令需要用户明确删除意图和 CLI `--yes`。任何 POST/PUT/DELETE 网络结果不确定时不得自动重试；返回 `UNKNOWN_WRITE_RESULT` 后，后续写入前应显式只读确认状态。
