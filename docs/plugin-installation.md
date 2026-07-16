# Codex 插件安装

本插件依赖仓库中的开源 CLI。请先安装 Python 3.11 或更高版本及 `pipx`，然后直接从 GitHub 功能分支安装：

```shell
pipx install "git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source"
```

当前项目尚未发布到 PyPI。私有仓库用户需要拥有该仓库的读取权限，并为 Git 配置可用于 GitHub 的已认证凭据。

添加唯一名称为 `zentao-team` 的团队 Marketplace：

```shell
codex plugin marketplace add "wwtweiwenting/zentao-ai-assistant@feature/zentao-open-source"
```

Codex CLI 0.130.0 没有插件安装子命令。添加 Marketplace 后，打开 Codex app 的 Plugins 页面，从 `Zentao Team` Marketplace 选择并启用 `zentao-ai-bug`；不要运行不存在的 CLI 安装命令。

在项目的 `.codex/zentao-ai-bug.yaml` 中保存非敏感配置。账号凭据应通过 CLI 的系统凭据存储流程配置，不要写入仓库、插件、命令历史或聊天内容。

安装或更新后请创建一个 new task，确认技能已加载，并先执行只读查询或 `zentao-ai doctor`。Windows、macOS 和 Linux 使用相同命令；Windows PowerShell 中若 `pipx` 尚未加入 PATH，请按 pipx 输出重开终端后再验证。

插件只允许受合同约束的有限写操作。删除 Bug 永久禁止；定时任务保持只读，交互写入仍要求当前任务中的精确授权、最新快照复核和幂等门禁。
