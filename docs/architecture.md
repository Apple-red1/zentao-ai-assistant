
# 架构

当前合同入口：[`docs/current-contract.md`](current-contract.md)。本页只记录真实
调用链；历史迁移决策见归档的 `skills/zentao/RULES.md`，不作为当前规则。

```text
用户 / AI
  -> skills/zentao/SKILL.md
  -> scripts/zentao.py
  -> cli/<resource>/commands.py
  -> services/<resource>/service.py
  -> internal/zentao/<resource>.py
  -> internal/zentao/session.py
  -> internal/http/client.py
  -> ZenTao API v2
```

依赖只向下。CLI/Services 不拼接 API URL，HTTP 层不知道领域资源。领域 endpoint 在 Internal 层显式实现，`endpoints.json` 不参与运行时路由。

当前 catalog 覆盖 20 个资源、120 个 endpoint；Fake、合同和 CLI E2E 以完整覆盖
门禁验证，官方合同快照与 21.7.8 兼容性观察分别管理。

## 对象关联资源增强链路

`resource fetch` 不进入官方 endpoint catalog。它仍遵守 `cli -> services -> internal/zentao -> internal/http` 依赖方向，但作为一个明确的只读资源获取操作，会先读取目标对象详情，再从附件区和富文本发现资源，最后通过 HTTP 层流式写入项目 `.tmp/zentao-resources/`。
