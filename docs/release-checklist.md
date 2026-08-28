# 发布检查清单

## Plugin / Clone surface

- [ ] 本次项目修改已按 SemVer minor（次版本）递增插件版本；`plugin.json`、`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json` 的 `version` 完全一致。
- [ ] 根目录 `plugin.json`、`.claude-plugin/plugin.json`、
  `.claude-plugin/marketplace.json`、`.codex-plugin/plugin.json` 和
  `.agents/plugins/marketplace.json` 与 `docs/current-contract.md` 同步。
- [ ] 仓库根目录 `skills/` 精确包含六个正式 Skill；`skills/_shared/zentao/`
  没有 `SKILL.md`，不成为公开 Skill；不存在第二份 Skills tree。
- [ ] Clone 的 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md` 路由不复制业务规则；Gemini
  Plugin/Extension、Cursor/Copilot/VS Code Plugin 不写成 v1 已验证支持。
- [ ] Claude real host gate 已真实执行 validate、load、install、discovery，且
  宿主 cache 副本仍能运行共享 scripts/_shared；否则记录 `BLOCKED_ENVIRONMENT`。
- [ ] Codex real host gate 已真实执行 marketplace add/install/discovery，且
  宿主 cache 副本仍能运行共享 scripts/_shared；否则记录 `BLOCKED_ENVIRONMENT`。
- [ ] Claude/Codex host cache 中没有 `.env`、password、Token 或持久运行数据；
  user config/cache/tmp 全部位于 `~/.zentao-ai-assistant/`。

## 架构与安全

- [ ] API 基础实现位于 `skills/zentao/`；高层能力位于各自 Skill / `skills/_shared/zentao/`，不存在 MCP Server、独立 `src/zentao_ai/` 主实现或系统级 `zentao-ai` 产品入口。
- [ ] 运行时与测试只使用 Python 标准库。
- [ ] `.env.example` 只有三项连接模板，真实 `.env` 不进入 Git。
- [ ] CLI/Services 不直接使用 `urllib` 或拼接 `/api.php/v2`。
- [ ] Token 不写回 `.env`；若启用 `.tmp/zentao/auth/` 短期缓存，则权限、TTL、401 刷新和脱敏合同均通过。
- [ ] 所有 R3 delete 在缺少 `--yes` 时不发送业务 HTTP。
- [ ] 写入网络不确定返回 `UNKNOWN_WRITE_RESULT`，不自动重试、不自动 GET。
- [ ] ZenTao 21.7.8 Bug 附件上传的 v2 空响应兼容路径仅在一次回读确认未落库后提交固定
  `bug/edit` `files[]` 表单，并通过 API 回读确认；页面会话不接受任意 URL、不泄露密码。
- [ ] `.tmp/` 已被 Git 忽略；`resource fetch` 只能从对象附件区/富文本发现资源，并拒绝跨源 URL/重定向。
- [ ] 资源文件流式写入项目 `.tmp/zentao-resources/`，同名文件不覆盖；空响应、登录/错误 HTML 和 MIME 冲突按 `RESOURCE_CONTENT_INVALID` 进入 `partial_failures`。
- [ ] `zentao-batch-export` 只写当前 scope 的 `zentao/zentao-batch-export/<run-id>/`，ZIP 动态命名；资源复制拒绝符号链接/目录逃逸，单项失败继续并完整记录到 manifest。
- [ ] user scope 使用 `~/.zentao-ai-assistant/cache/auth/`、
  `~/.zentao-ai-assistant/tmp/`，目录/文件权限目标仍为 `0700`/`0600`；config
  选择不混用多个文件。

## 全量覆盖

执行：

```bash
python tests/run_all.py

# API endpoint 专项仍可单独执行
python skills/zentao/tests/run_all.py
```

必须同时得到：Catalog、Internal、CLI、Skill routes、Fake API、Contract tests、CLI E2E 均为 `120 / 120`，`Real API calls: 0`，最终 `Result: PASS`；同时 `resource fetch` 的资源发现、二进制下载、部分失败和同源安全 E2E 必须通过。

完整回归还必须按 `docs/testing.md` 保留 L0-L5 证据；静态 manifest/JSON 或单元
测试通过不能替代 Claude/Codex real host gate。宿主命令、安装 surface 或缓存
检查不可用时，发布状态必须是 `BLOCKED_ENVIRONMENT`，不能标记 Plugin support
为已验收。

另外检查报告中的 `Official snapshot` 与 `Specific sources`。前者是 runtime
catalog 与独立官方快照的比对，后者只统计有 endpoint-specific 官方 deep link 的
条目；generic index URL 必须带明确的待核对说明，不能伪装成已逐项验证。

## 兼容性

自动化发布门槛使用完整本地 Fake ZenTao。真实 ZenTao 21.7.8 或其他版本的差异根据实际运行证据记录在独立的 `skills/zentao/references/compatibility/` evidence 文件中；必要时再同步 `endpoints.json` 的 compatibility 元数据，不用 Fake 结果冒充真实实例兼容性。

所有自动化和 Fake 测试都不得连接真实 ZenTao；发布前审计还需确认无第三方
Python runtime 依赖、无 MCP、无 secret 泄露、无调试输出和无遗留 `__pycache__`。
