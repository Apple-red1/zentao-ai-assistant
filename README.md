# 每日工作

此目录是禅道每日自动化的独立 Codex 项目，不属于任何业务代码仓库。

- `个人每日 Bug AI 处理助手`：默认执行模式，使用 `personal.scopeNames`，报告写入 `reports/personal`。
- `团队每日 Bug 汇总助手`：严格只读，使用 `team.scopeNames`，报告写入 `reports/team`。
- 两个任务每天 `08:00`（Asia/Shanghai）运行。
- 业务仓库只作为个人 Bug 路由后的代码处理目标；自动化配置和报告不存入业务仓库。
- 报告由 `scripts/render-report.py` 按 `templateVersion=v2` 固定渲染。

测试命令：

```powershell
python -m unittest discover -s tests -v
```

Use `zentao-ai auth login --kind password` once to store the ZenTao password
in the system credential store. If no API token is configured, the runtime
logs in via `/api.php/v2/users/login` and caches only the returned token in
memory; the password is never written to config, logs, or results.
