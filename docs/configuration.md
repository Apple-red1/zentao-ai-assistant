# 本地配置

默认路径为 `~/.codex/zentao-ai-bug/config.yaml`。设置环境变量 `ZENTAO_CONFIG` 可覆盖路径。推荐始终使用 `zentao-ai setup` 创建或更新，不要手写秘密。

## 示例

```yaml
version: 1
zentao:
  base_url: https://zentao.example.com
  api_version: v2
  account: my-account
team:
  members:
    - name: 张三
      account: zhangsan
query:
  default_status: unresolved
  page_size: 100
  max_results: 500
writes:
  enabled: true
```

## 字段

| 字段 | 说明 |
|---|---|
| `version` | 配置格式版本，当前固定为 1。 |
| `zentao.base_url` | 禅道站点根地址，必须使用 HTTP 或 HTTPS；生产环境应使用 HTTPS。 |
| `zentao.api_version` | 当前固定为 `v2`。 |
| `zentao.account` | 个人禅道账号；“我/自己”的查询使用此账号。 |
| `team.members` | 团队成员数组，每项含显示姓名 `name` 和禅道账号 `account`。 |
| `query.default_status` | 默认状态，通常使用 `unresolved`。 |
| `query.page_size` | 每页读取数量，范围 1–1000。 |
| `query.max_results` | 单次最多返回数量，范围 1–5000。 |
| `writes.enabled` | 是否允许备注、编辑、激活和指派；关闭后所有写工具拒绝执行。 |

团队成员只影响“团队”查询。查询指定姓名或账号时可直接查内部或外部人员，不要求先加入 `members`。

## 密码与 Token

`zentao-ai setup` 把密码保存到 macOS Keychain、Windows Credential Manager 或 Linux Secret Service。`ZENTAO_PASSWORD` 只作为当前进程的后备输入，适用于短期自动化。

Token 由插件自动取得并缓存在系统凭据库；401 时清除旧值、重新登录一次并重放原请求一次。配置文件拒绝任何密码、Token、Cookie 或 Authorization 字段。

## 更新

```bash
zentao-ai setup --update
zentao-ai doctor
```

更新现有配置时不会把秘密写回 YAML。配置文件保存权限在支持的平台上设为 `0600`。
