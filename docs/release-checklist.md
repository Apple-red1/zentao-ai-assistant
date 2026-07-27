# 发布检查清单

## 代码与安全

- [ ] 所有行为先有失败测试，再有实现。
- [ ] `python -m pytest -v` 全部通过；仅缺少本机 PowerShell 时允许相应测试跳过。
- [ ] Ruff、mypy、build、twine check 全部通过且无警告。
- [ ] plugin-creator validator 与 Skill validator 通过。
- [ ] 仓库秘密合同、工作树扫描和 Git 历史扫描无真实秘密、内部地址、真实人员或业务 Bug。
- [ ] MCP、Skill、CLI 和 Python 服务均没有删除 Bug 能力。

## 安装与文档

- [ ] macOS/Linux 安装器可连续运行两次。
- [ ] Windows PowerShell 安装器在 Windows CI 可连续运行两次。
- [ ] README 从 clone 到 doctor 的命令与当前实现一致。
- [ ] 默认配置只含非秘密字段；密码与 Token 只进入系统凭据库。
- [ ] 安装后在新 Codex 任务中可看到 10 个 MCP 工具。

## 禅道 21.7.8 实例

- [ ] `zentao-ai doctor` 的强制检查全部 PASS。
- [ ] 个人、团队、外部人员、组合条件和单 Bug 查询通过。
- [ ] 备注、编辑、激活、指派在专用测试 Bug 上通过。
- [ ] 过期 Token 只触发一次重新登录和一次请求重放。
- [ ] 写超时返回 `UNKNOWN_WRITE_RESULT`，没有重复写入。

真实实例验收必须使用本地 `zentao-ai setup`。验收记录不得包含真实 URL、账号、姓名、Bug ID、响应正文或任何凭据。
