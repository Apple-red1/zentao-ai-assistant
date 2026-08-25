
# 测试

测试使用 `unittest`、`http.server`、`subprocess` 等标准库能力。

- T0：catalog 120/120 与集合一致性。
- T1：配置、参数转换、输出和错误纯单元测试。
- T2：有状态 Fake ZenTao 120/120 路由。
- T3：Internal adapter 合同测试。
- T4：真实 CLI subprocess E2E 120/120。
- T5：典型多步 Skill 场景。

合同测试还会读取独立的 `skills/zentao/references/api-v2/official-contract.json`。
它是人工核对的官方 API v2 evidence snapshot，不参与运行时路由，也不从
`endpoints.json` 生成。测试报告将实现覆盖（各 surface 的 120/120）、官方快照
匹配数和 endpoint-specific deep-link 数分开显示。ZenTao 21.7.8 的真实观察只记录
在 `skills/zentao/references/compatibility/zentao-21.7.8.json`，不会覆盖官方合同。
报告还会输出 `21.7.8 observed/unsupported/not observed` 三项状态；catalog、evidence
和验收文档的统计由 compatibility contract test 交叉校验。

配置和用户文本文件的非法 UTF-8 也属于输入边界合同：`.env` 返回
`CONFIG_ERROR`，`--steps-file` / `--comment-file` 等返回 `USAGE_ERROR`，均保持
`--json` 的 stdout/stderr 分流且不输出 traceback。

Fake 每条合同/E2E 前重置为确定性状态；自动化测试不登录或访问真实 ZenTao。
