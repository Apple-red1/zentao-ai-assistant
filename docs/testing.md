# 测试

测试使用 `unittest`、`http.server`、`subprocess` 等标准库能力。

- T0：catalog 120/120 与集合一致性。
- T1：配置、参数转换、输出、错误和资源发现纯单元测试。
- T2：有状态 Fake ZenTao 120/120 路由，并额外提供受控二进制资源响应/重定向用于资源下载合同。
- T3：Internal adapter 合同测试。
- T4：真实 CLI subprocess E2E 120/120，以及 `resource fetch` 的附件区 + 富文本、data URI、部分失败、同名文件和同源安全场景。
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

## ZenTao 21.7.8 资源兼容测试

资源下载实现完成后仍需要在专用 ZenTao 21.7.8 测试实例验证真实运行差异，至少覆盖：

1. 对象详情中附件区 `files` 的真实字段和下载地址；
2. 富文本内联图片和文件链接的真实 URL 形式；
3. 资源请求是否接受 API Token，是否额外依赖 Cookie/Web Session；
4. 30x 跳转链以及最终地址是否仍处于同源可信范围；
5. `Content-Type`、`Content-Disposition`、中文/空格文件名；
6. 图片、PDF、文本/日志、Office/压缩包等不同文件类型；
7. 同名文件、单个失败/部分失败和全部失败；
8. 大文件流式落盘行为。

真实兼容测试只能通过 ZenTao 公开访问路径执行，不读取或修改 ZenTao 内部数据库。未实际执行前不得标记为 `verified`。
