# 本地配置

长期连接配置严格选择一个文件，再叠加同名环境变量：

1. `ZENTAO_CONFIG_FILE` 非空时，读取它；文件不存在直接返回 `CONFIG_ERROR`；
2. 否则，仓库根目录 `.env` 存在时读取它；
3. 否则，读取 `~/.zentao-ai-assistant/config.env`。

不会在多个文件之间补字段。`ZENTAO_BASE_URL`、`ZENTAO_ACCOUNT`、
`ZENTAO_PASSWORD` 环境变量覆盖所选文件中的同名值；环境变量优先级不改变
配置文件选择。显式指定非仓库根目录配置文件时，连接读取该文件，运行数据使用
user scope。

project scope 的配置示例（只填写本地秘密，不要提交真实值）：

```dotenv
ZENTAO_BASE_URL=https://zentao.example.com
ZENTAO_ACCOUNT=your-account
ZENTAO_PASSWORD=your-password
```

user scope 的文件路径为 `~/.zentao-ai-assistant/config.env`，键名相同。使用
`zentao.py setup`（project）或 `zentao.py setup --scope user`（user）生成，
密码通过交互式提示输入，不提供命令行 password 参数。写入后必须显式运行
`zentao.py doctor --json`；doctor 和错误输出不显示密码或 Token。

配置文件使用受限、对称的 dotenv codec，并以安全原子写入保存；POSIX 目标权限
为 `0600`。配置目录和运行目录为 `0700`。

`.env` 与 `.env.*` 被 Git 忽略，`.env.example` 明确保留。不得提交真实站点秘密。

## Runtime paths

| 数据 | project scope | user scope |
|---|---|---|
| 配置 | `<repo>/.env` | `~/.zentao-ai-assistant/config.env` |
| Token cache | `<repo>/.tmp/zentao/auth/` | `~/.zentao-ai-assistant/cache/auth/` |
| 高层临时材料 | `<repo>/.tmp/zentao/<skill>/` | `~/.zentao-ai-assistant/tmp/zentao/<skill>/` |
| resource fetch | `<repo>/.tmp/zentao-resources/` | `~/.zentao-ai-assistant/tmp/zentao-resources/` |

project scope 适合直接 clone；Plugin 或独立用户运行适合 user scope。Plugin
升级只替换宿主 Plugin cache 中的插件副本，不删除或迁移
`~/.zentao-ai-assistant/config.env`、`cache/` 或 `tmp/`。

## Token 与临时数据

业务请求通过 `POST /api.php/v2/users/login` 获取 Token。Token 不写入 `.env`。

为了让多个独立 Skill/CLI 进程减少重复登录，Token 默认可以短期缓存在上述
scope 对应的 cache 目录：

```text
project: <repo>/.tmp/zentao/auth/
user:    ~/.zentao-ai-assistant/cache/auth/
```

缓存按站点 + account 隔离，默认本地 TTL 8 小时；服务端若提前使 Token 失效，
明确 401 会触发一次重新登录。缓存不保存密码，项目 `.tmp/` 和用户 `tmp/`
都不是长期事实源。

`ZENTAO_TOKEN_CACHE_DIR` 和 `ZENTAO_TOKEN_CACHE_DISABLED=1` 是内部运行/测试覆盖开关，不属于长期连接配置事实源。

## CI / tests

CI 和自动化测试使用临时 HOME 或 `ZENTAO_CONFIG_FILE` 指向临时配置，并使用
loopback Fake ZenTao；不得读取真实 `.env`、写入宿主 Plugin cache 或连接真实
ZenTao。临时配置仍只包含测试值，测试结束后清理。
