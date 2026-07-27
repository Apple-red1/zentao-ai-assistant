# 安装与升级

## 前置条件

- 禅道开源版 21.7.8（首要兼容目标），API v2 可访问。
- Python 3.11 或更高版本。
- Codex CLI 可在终端运行。
- macOS/Linux 使用 POSIX shell；Windows 使用 PowerShell。
- 对 GitHub 仓库具有读取权限。

## 自动安装

macOS/Linux：

```bash
./scripts/install.sh
```

Windows：

```powershell
.\scripts\install.ps1
```

脚本使用 pipx 隔离安装 Python 包，然后运行：

```bash
codex plugin marketplace add "仓库绝对路径"
codex plugin add zentao-ai-bug@zentao-ai-assistant
```

默认模式接着运行 `zentao-ai setup` 与 `zentao-ai doctor`。自动化环境可传 `--non-interactive` 或 `-NonInteractive`；已有配置时仍会运行 doctor，没有配置时只输出下一步命令。

## 手动安装

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install --force .
codex plugin marketplace add "$PWD"
codex plugin add zentao-ai-bug@zentao-ai-assistant
zentao-ai setup
zentao-ai doctor
```

Windows 可把 `python3` 替换为 `py -3.11`，把 `$PWD` 替换为仓库绝对路径。

## 升级

在同一仓库执行：

```bash
git pull --ff-only
./scripts/install.sh --non-interactive
```

安装器可重复运行，并使用 `pipx install --force` 更新本地命令。更新后重启 Codex 或新建任务，让 Codex 重新加载插件和 MCP 工具。

## 卸载

```bash
codex plugin remove zentao-ai-bug
python3 -m pipx uninstall zentao-ai-assistant
```

本地配置和系统凭据不会自动删除，便于重装。确认不再需要后再通过操作系统凭据管理器和文件管理器手动清理。
