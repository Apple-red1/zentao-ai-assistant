# 排错指南

先运行：

```bash
python skills/zentao/scripts/zentao.py doctor --json
```

| 错误码 | 含义 | 处理 |
|---|---|---|
| `CONFIG_ERROR` | 当前选中的配置源缺少字段或 URL 无效 | 按 [configuration.md](configuration.md) 检查 `ZENTAO_CONFIG_FILE` → repo `.env` → Home config 的选择顺序；只报告缺少的键名，不打印配置内容。 |
| `USAGE_ERROR` | 参数、scope、枚举或删除确认不符合 CLI 合同 | 执行对应 `<resource> <action> --help`。 |
| `RESOURCE_SECURITY_ERROR` | 对象资源地址或重定向超出当前 ZenTao 同源可信范围 | 检查对象富文本/附件 URL；不要绕过同源校验。 |
| `RESOURCE_FETCH_FAILED` | 已发现对象资源，但全部获取失败 | 查看 `details.partial_failures`，按各资源错误处理。 |
| `API_ERROR` | ZenTao 明确返回 HTTP/业务失败 | 根据 `details.status` 与最小必要响应信息检查权限、ID 和字段。 |
| `NETWORK_ERROR` | 请求确定未送达或 GET 重试耗尽 | 检查地址、DNS、TLS、网络和反向代理。 |
| `MALFORMED_RESPONSE` | API 返回无法解析的 JSON | 记录目标实例版本和 endpoint，作为兼容性差异处理。 |
| `UNKNOWN_WRITE_RESULT` | 写请求可能已经执行但响应不可确认 | 不要直接重放；先显式使用对应 view/list 读取当前状态，再决定后续动作。 |

自动化测试问题请运行：

```bash
python tests/run_all.py

# 仅检查 API endpoint surface 时：
python skills/zentao/tests/run_all.py
```

覆盖摘要任一 surface 低于 120/120 都应视为失败。

## 配置源与运行目录

- 设置了 `ZENTAO_CONFIG_FILE` 时只读取该文件；路径不存在或不可读会失败，
  不会从其它文件补字段。
- 未设置显式路径时，仓库根目录 `.env` 存在就会覆盖 Home config。这是
  Clone/project 的预期行为；Plugin 首次配置应运行
  `zentao.py setup --scope user`，并确认执行脚本所在的 Plugin root 没有被误当作
  project 配置源。
- user scope 的配置、Token/cache/tmp 都在
  `~/.zentao-ai-assistant/`；Plugin cache 不应出现 `.env`、密码或 Token。
- 如果 Home 目录不可写或权限过宽，修复用户 runtime 根目录的可写性和 POSIX
  `0700` 目录权限；配置/Token 文件应为 `0600`。不要把秘密放入命令行。

## Skill 或宿主发现不完整

发现结果必须精确包含五个正式 Skill：`zentao`、`zentao-statistics`、
`zentao-personal`、`zentao-project-management`、`zentao-bug-resolver`。
`skills/_shared/zentao/` 没有 `SKILL.md`，不应被安装为公开 Skill。先检查
宿主安装记录、marketplace 条目和缓存中的根目录结构；不要复制第二份
`skills/` 来绕过发现问题。

## Plugin validate / install 失败

先使用当前客户端检查 manifest 与版本：

```bash
claude plugin validate .
claude plugin marketplace list
codex plugin marketplace list
```

确认运行目录是仓库根目录，Claude 的 `.claude-plugin/marketplace.json` 和
Codex 的 `.agents/plugins/marketplace.json` 都存在，且 marketplace 只有一个
根插件条目。升级宿主后重新验证；不要以 MCP 旁路或手工复制 Skill 替代
Plugin validate/install/discovery。
