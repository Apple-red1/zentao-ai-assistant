# Contributing

修改前请阅读根目录 [`AGENTS.md`](AGENTS.md) 和目标 Skill 的 `SKILL.md`。

- API endpoint 变更必须完整传播 catalog / adapter / Service / CLI / Fake / tests / docs。
- 高层 Skill 不得直接访问 ZenTao HTTP/Internal；使用 `zentao_skill.public`。
- 只使用 Python 标准库。
- 提交前运行 `python tests/run_all.py`。
- API surface 变更额外关注 `python skills/zentao/tests/run_all.py` 的 120/120 门槛。
