
# zentao Skill

本仓库提供单一 `skills/zentao/` Skill，通过 Python 标准库直接调用 ZenTao 官方 API v2。运行时不依赖 MCP、独立 `zentao-ai` 系统 CLI 或第三方 Python 包。

## 配置

复制 `.env.example` 为 `.env`，填写：

```dotenv
ZENTAO_BASE_URL=https://zentao.example.com
ZENTAO_ACCOUNT=your-account
ZENTAO_PASSWORD=your-password
```

`.env` 不提交。登录使用 `POST /api.php/v2/users/login`，Token 只存在当前 Python 进程内存中。

## 使用

```bash
python skills/zentao/scripts/zentao.py doctor --json
python skills/zentao/scripts/zentao.py bug list --product 1 --json
python skills/zentao/scripts/zentao.py bug view 123 --json
python skills/zentao/scripts/zentao.py task start 88 --real-started "2026-08-25 09:00:00" --json
```

删除接口属于 R3：只有明确删除意图时使用，并额外要求 `--yes`：

```bash
python skills/zentao/scripts/zentao.py bug delete 123 --yes --json
```

参数以 `<resource> <action> --help` 为准。资源导航见 `skills/zentao/references/api-v2/`；机器覆盖索引见 `endpoints.json`。

## 测试

完整自动化测试只连接进程内本地 Fake ZenTao，不访问真实 ZenTao：

```bash
python skills/zentao/tests/run_all.py
```

当前能力基线：20 个资源、120 个官方 API v2 endpoint。真实 ZenTao 21.7.8 的兼容性差异只根据实际运行证据记录，不由 Fake 测试冒充。
