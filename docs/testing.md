
# 测试

测试使用 `unittest`、`http.server`、`subprocess` 等标准库能力。

- T0：catalog 120/120 与集合一致性。
- T1：配置、参数转换、输出和错误纯单元测试。
- T2：有状态 Fake ZenTao 120/120 路由。
- T3：Internal adapter 合同测试。
- T4：真实 CLI subprocess E2E 120/120。
- T5：典型多步 Skill 场景。

Fake 每条合同/E2E 前重置为确定性状态；自动化测试不登录或访问真实 ZenTao。
