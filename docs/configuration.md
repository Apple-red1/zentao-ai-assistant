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

## 个人默认团队

`zentao-personal` 的长期团队名单独立于三项连接配置，不增加 `.env` 键。
Clone/project 与 Plugin/user 都固定保存到：

```text
~/.zentao-ai-assistant/teams/<identity-sha256>.json
```

身份通过 public facade 的 `connection_identity` 读取当前实际选中的连接配置：
URL scheme/host 小写、去默认端口、去路径末尾 `/`，保留安装路径和非默认端口；
拒绝地址内的凭据、query、fragment。哈希输入为排序键、紧凑 JSON 编码的
`{base_url, account}`；account 区分大小写。不同实例或账号互不混用名单。

文件 schema 为 `{schema_version: 1, owner: {base_url, account}, members: [account, ...]}`，
不保存密码、Token、姓名或本人账号副本。本人由查询时自动合并；文件不存在表示
配置成员为空，查看不创建文件。只支持一个默认团队，不涉及旧数据迁移或云同步。

目录 0700、文件 0600，原子替换；符号链接、非普通文件、超过 1 MiB、损坏 JSON、
未知 schema 或归属冲突均阻止读取/覆盖，不自动清空。每身份的 `.lock` 目录保护
本地读改写；竞争返回 `TEAM_CONFIG_BUSY`。异常退出遗留锁需人工确认进程已退出
后处理，不自动删除/抢占。升级只替换插件代码，不删除 `teams/`。

名单修改前完整解析真实用户目录，任一输入失败不写入；完整替换空名单须显式
`team-replace --clear`。维护命令与结果详见
[团队合同](../skills/zentao-personal/references/team.md)。

## 测试端工作台配置

`zentao-testing` 的 Project/Module 上下文独立保存到：

```text
~/.zentao-ai-assistant/testing-projects/<identity-sha256>.json
```

身份键是规范化 base URL 与区分大小写的当前 account；文件不保存密码、Token 或姓名。
目录/文件权限为 `0700/0600`，使用锁目录和原子替换，并校验 schema、owner、大小、普通
文件和符号链接。Project 绑定一个 Product 与默认 `affected-build`；模块保存真实
Module ID 及前后端 account。Project ID 可选；提供 Project ID 时，Project/Product/Module
关联无法由当前只读返回值证明，命令会显式返回 `complete=false`，不会把未验证事实当成已验证；
未提供 Project ID 时不要求 Project/Product 关联。Project 更新会使已有
模块 stale，须重新设置模块。

### 测试团队

`zentao-testing` 的测试团队独立保存到：

```text
~/.zentao-ai-assistant/testing-teams/<identity-sha256>.json
```

该配置与开发/个人团队的 `teams/`、测试项目上下文的 `testing-projects/` 分离。它包含一份
全局默认测试团队和可选的每项目完整覆盖；项目覆盖存在时不与全局名单合并，不存在时才回退
全局名单。当前登录账号仅在查询时自动包含，不写入成员列表。

测试团队成员保存前必须经过完整用户目录的 account/唯一姓名解析。只有明确的
`team-import-personal` 请求才会把个人团队一次性复制到全局测试团队，之后不自动同步。配置
使用与个人团队相同的身份隔离、`0700/0600` 权限、锁、原子替换、损坏保护和 symlink 拒绝规则；
目标域失败不会覆盖另一团队配置。
