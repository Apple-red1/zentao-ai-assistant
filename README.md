# 禅道 AI Bug 助手（Codex 插件）

在 Codex 里用一句话查询和安全更新禅道 Bug。支持查询自己的未关闭 Bug、配置团队的 Bug、团队外部人员的 Bug、任意条件组合与单个 Bug 详情；支持添加备注、编辑白名单字段、激活和指派。

首要兼容目标是禅道开源版 **21.7.8** 和 API v2。账号、密码与 Token 都只在本机使用；仓库和 YAML 不保存秘密。

## 三分钟开始

准备好以下内容：禅道地址、个人账号和密码、Python 3.11+、已安装的 Codex CLI，以及这个 GitHub 仓库的读取权限。

### macOS / Linux

```bash
git clone https://github.com/wwtweiwenting/zentao-ai-assistant.git
cd zentao-ai-assistant
./scripts/install.sh
```

### Windows PowerShell

Windows 安装入口是 `scripts/install.ps1`：

```powershell
git clone https://github.com/wwtweiwenting/zentao-ai-assistant.git
cd zentao-ai-assistant
.\scripts\install.ps1
```

安装器会隔离安装 `zentao-ai`、注册当前仓库 Marketplace、安装 `zentao-ai-bug@zentao-ai-assistant`，然后启动配置与检查。也可以分开执行：

```bash
./scripts/install.sh --non-interactive
zentao-ai setup
zentao-ai doctor
```

默认本地配置文件是 `~/.codex/zentao-ai-bug/config.yaml`；可用 `ZENTAO_CONFIG` 指定其他位置。配置时只输入禅道地址、个人账号、隐藏密码和可选团队成员；密码进入系统凭据库，不进入配置文件。

安装后重启 Codex 或**新建任务**，即可这样说：

- “查询我未关闭的 Bug，汇总状态和严重程度。”
- “查询团队成员未关闭的 Bug，按指派人汇总。”
- “查询外部人员王小明的 Bug 清单。”
- “查询产品 3 中严重程度为 1、标题含登录的未关闭 Bug。”
- “给 Bug 123 添加备注：请补充日志。”

## 写入安全

备注、编辑、激活和指派只在当前消息明确包含 Bug ID、动作和必要参数时执行。写请求超时不会自动重试；删除永久不支持。当前版本也不提供创建、解决或关闭工具。

## 文档

- [安装与升级](docs/installation.md)
- [本地配置](docs/configuration.md)
- [功能与示例](docs/features.md)
- [安全模型](docs/security.md)
- [排错指南](docs/troubleshooting.md)

许可证：Apache-2.0。安全问题请参阅 [SECURITY.md](SECURITY.md)。
