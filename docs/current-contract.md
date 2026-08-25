# ZenTao Skill 当前合同入口

> 状态：**CURRENT / 当前唯一权威入口**  
> 更新日期：2026-08-25  
> 适用范围：仓库中的 `zentao` Skill、其 CLI、API v2 合同、测试和发布检查。

本页是“现在应该相信什么”的索引。历史设计文档可以追溯决策，但不能覆盖本页
指向的源码、测试或合同文件。发现冲突时，先修正文档或测试，不能把历史限制重新
当成现行能力。

## 权威文件及职责

| 范围 | 当前事实来源 |
|---|---|
| AI/Skill 调用、风险等级、授权和输出 | [`skills/zentao/SKILL.md`](../skills/zentao/SKILL.md) |
| endpoint method/path/参数/兼容元数据 | [`skills/zentao/references/api-v2/endpoints.json`](../skills/zentao/references/api-v2/endpoints.json) |
| 独立官方 API v2 evidence | [`skills/zentao/references/api-v2/official-contract.json`](../skills/zentao/references/api-v2/official-contract.json) |
| 真实 ZenTao 21.7.8 观察 | [`skills/zentao/references/compatibility/zentao-21.7.8.json`](../skills/zentao/references/compatibility/zentao-21.7.8.json) 与 [`docs/acceptance/zentao-21.7.8.md`](acceptance/zentao-21.7.8.md) |
| 工程约束、分层、安全和交付门槛 | [`AGENTS.md`](../AGENTS.md) |
| 目录职责概览 | [`docs/architecture.md`](architecture.md) |

`skills/zentao/RULES.md` 是 **ARCHIVED / 历史迁移快照**，已被本页和后续实现
supersede；不要再把它作为当前源码事实或开发限制的引用来源。

## 当前实现事实

- 产品边界是单一 `skills/zentao/` Skill；公开入口是
  `python3 skills/zentao/scripts/zentao.py <resource> <action> ... --json`。
- catalog 覆盖 20 个资源、120 个 ZenTao API v2 endpoint；实现、CLI、Skill 路由、
  Fake、合同测试和 CLI E2E 需要保持 `120/120`。
- 运行时与测试只使用 Python 标准库；不恢复 MCP Server、独立系统级
  `zentao-ai` 命令或第三方运行时依赖。
- R3 delete 是现行能力，但必须有用户明确删除意图和 CLI `--yes`；未确认时在
  业务 HTTP 之前拒绝。
- 写请求不自动重试；结果不确定返回 `UNKNOWN_WRITE_RESULT`，不自动重放或追加
  GET。GET 只按既有规则有限重试。
- 全量门禁命令为：
  `python3 skills/zentao/tests/run_all.py`，必须报告各实现 surface `120/120`、
  `Real API calls: 0` 和 `Result: PASS`；官方快照匹配及 specific source 数单独报告。

## 文档生命周期

新的设计或 Issue 完成后，文档必须明确标记为 `CURRENT`、`SUPERSEDED BY #N`
或 `ARCHIVED`。如果更新了 endpoint、CLI、安全语义或兼容观察，要同时更新其
对应的 catalog、evidence、测试和文档，不得只改一份描述。

Issue #13 等历史讨论若需要引用规则，应引用本页及当前源码；不能再引用归档的
`RULES.md` 作为“当前事实”。
