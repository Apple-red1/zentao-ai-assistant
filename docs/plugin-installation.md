# Codex 插件安装

本插件依赖开源 CLI。请先安装 Python 3.11 或更高版本及 `pipx`，然后运行：

```shell
pipx install zentao-ai-assistant
```

开发分支可使用下列形式安装；把 `<branch>` 换成要验证的分支名：

```shell
pipx install git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@<branch>
```

从仓库根目录添加团队 Marketplace，再安装插件：

```shell
codex plugin marketplace add .
codex plugin add zentao-ai-bug@personal
```

在项目的 `.codex/zentao-ai-bug.yaml` 中保存非敏感配置。账号凭据应通过 CLI 的系统凭据存储流程配置，不要写入仓库、插件、命令历史或聊天内容。

安装或更新后请创建一个 new task，确认技能已加载，并先执行只读查询或 `zentao-ai doctor`。Windows、macOS 和 Linux 使用相同命令；Windows PowerShell 中若 `pipx` 尚未加入 PATH，请按 pipx 输出重开终端后再验证。

插件只允许受合同约束的有限写操作。删除 Bug 永久禁止；定时任务保持只读，交互写入仍要求当前任务中的精确授权、最新快照复核和幂等门禁。
