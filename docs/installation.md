# 使用与环境

## 前置条件

- Python 3.11 或更高版本。
- 可访问目标 ZenTao API v2 的网络环境。
- 项目根目录 `.env` 已按 [configuration.md](configuration.md) 配置。

本项目不需要 `pip install`、pipx、MCP Server、Codex marketplace 插件或系统级 `zentao-ai` 命令。

## 运行

```bash
python skills/zentao/scripts/zentao.py doctor --json
python skills/zentao/scripts/zentao.py bug list --product 1 --json
python skills/zentao/scripts/zentao.py task view 1 --json
```

从其他当前工作目录执行时也可以使用脚本绝对路径；配置定位不依赖 cwd。

## 测试

```bash
python tests/run_all.py

# 仅检查 API endpoint surface 时：
python skills/zentao/tests/run_all.py
```

自动化测试只连接测试进程内的 loopback Fake ZenTao，不访问真实 ZenTao。
