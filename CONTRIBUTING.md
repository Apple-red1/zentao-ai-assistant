
# 贡献指南

- Python 版本：3.11+；运行时和测试只使用标准库。
- 新增或修改 ZenTao endpoint 时，同时更新 capability catalog、显式 Internal adapter、CLI surface、Fake route、合同测试与 E2E 覆盖。
- `endpoints.json` 只能作为覆盖/审计索引，不能变成运行时万能 HTTP 路由表。
- 写请求不自动重试；DELETE 必须保留 `--yes` 门槛。
- 提交前运行 `python skills/zentao/tests/run_all.py`。
