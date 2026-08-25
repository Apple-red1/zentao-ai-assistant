# zentao-ai-assistant

当前行为与开发事实入口：[`docs/current-contract.md`](docs/current-contract.md)。

本仓库提供一组供 AI 使用的 ZenTao 项目管理 Skills：

- `zentao`：ZenTao API v2 原子读取/写入和附件资源能力；
- `zentao-statistics`：确定性统计、聚合和范围对比；
- `zentao-personal`：个人待办、风险、工作列表和摘要；
- `zentao-project-management`：Project / Execution 的进度事实、风险和工作量分析。

运行时只依赖 Python 3.11+ 标准库，不依赖 MCP 或第三方 Python 包。

## 配置

复制 `.env.example` 为 `.env`，填写 `ZENTAO_BASE_URL / ZENTAO_ACCOUNT / ZENTAO_PASSWORD`。Token 不写回 `.env`，允许短期缓存在 Git ignored 的 `.tmp/zentao/auth/`。

## API Skill

```bash
python skills/zentao/scripts/zentao.py doctor --json
python skills/zentao/scripts/zentao.py bug list --product 1 --json
python skills/zentao/scripts/zentao.py resource fetch --object-type bug --object-id 123 --json
```

删除属于 R3，必须有明确删除意图并传 `--yes`。

## 高层 Skill 示例

```bash
python skills/zentao-statistics/scripts/zentao_statistics.py summary bug --product 1 --json
python skills/zentao-personal/scripts/zentao_personal.py overview --json
python skills/zentao-project-management/scripts/zentao_project_management.py health --project 12 --json
```

详细自然语言边界见各 Skill 的 `SKILL.md`。

## 测试

```bash
python tests/run_all.py
```

`zentao` API 专项仍维持 20 个资源、120 个官方 API v2 endpoint 的完整覆盖门槛；高层 Skill 的场景测试单独统计，不能把 API `120/120` 解释为整个项目的用户场景覆盖率。
