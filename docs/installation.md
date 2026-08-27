# 使用与环境

## 前置条件

- Python 3.11 或更高版本。
- 可访问目标 ZenTao API v2 的网络环境。
- Clone 模式准备项目根目录 `.env`，Plugin 模式准备用户配置；详见
  [configuration.md](configuration.md)。

仓库根目录的 `.env.example` 只是三项键名模板；推荐使用下面的 `setup` 交互式
流程生成实际配置，不要把占位值当作连接信息。

本项目不需要 `pip install`、pipx、MCP Server、第三方 Python 包或系统级
`zentao-ai` 命令。Plugin 由 Claude Code / Codex 宿主按各自 marketplace 入口
加载，业务 Skill 仍来自仓库根目录的同一份 `skills/`。

## Clone / project

clone 后从仓库根目录运行：

```bash
python skills/zentao/scripts/zentao.py setup
python skills/zentao/scripts/zentao.py setup --scope project
python skills/zentao/scripts/zentao.py doctor --json
```

bare `setup` 与 `setup --scope project` 等价；密码只在交互式提示中输入。Claude
Code / Gemini CLI 的 clone 指令入口分别是 `CLAUDE.md` / `GEMINI.md`，两者都只
导入根 `AGENTS.md`。

## Claude Code Plugin

在包含 `.claude-plugin/marketplace.json` 的仓库根目录执行当前 Claude Code CLI
入口：

```bash
claude plugin validate .
claude --plugin-dir .
claude plugin marketplace add .
claude plugin install zentao-ai-assistant@zentao-ai-assistant
```

`--plugin-dir` 用于本地 load；marketplace 安装后可在 plugin details 中选择
安装 scope。安装完成后，若宿主提示 reload，按提示执行 `/reload-plugins`，再
开启新会话检查五个正式 Skill。Plugin 首次配置使用：

```bash
python skills/zentao/scripts/zentao.py setup --scope user
python skills/zentao/scripts/zentao.py doctor --json
```

## Codex Plugin

在仓库根目录登记 `.agents/plugins/marketplace.json`，再由 Codex plugin browser
完成安装：

```bash
codex plugin marketplace add .
codex plugin marketplace list
codex
```

在 Codex 中输入 `/plugins`，选择 `zentao-ai-assistant` marketplace 并安装；安装
后开启新会话检查五个正式 Skill。Codex repo marketplace 的单一条目通过
`source.path: "./"` 指向仓库根目录，不复制 `skills/` 到 marketplace 或 Plugin
cache。首次配置同样使用 `setup --scope user`，然后显式运行 `doctor --json`。

## 直接调用 Skill

从其他当前工作目录执行时可以使用脚本绝对路径；配置定位不依赖 cwd。

```bash
python skills/zentao/scripts/zentao.py bug list --product 1 --json
python skills/zentao/scripts/zentao.py task view 1 --json
```

Plugin cache 不承载 `.env`、Token 或密码；user runtime 始终位于
`~/.zentao-ai-assistant/`。

## 测试

```bash
python tests/run_all.py

# 仅检查 API endpoint surface 时：
python skills/zentao/tests/run_all.py
```

自动化测试只连接测试进程内的 loopback Fake ZenTao，不访问真实 ZenTao。
