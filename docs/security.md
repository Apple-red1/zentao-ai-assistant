# 安全模型

## 配置、长期秘密与认证

- project scope 配置是 `<repo>/.env`，user scope 配置是
  `~/.zentao-ai-assistant/config.env`；`.env.example` 只含三项占位键。
- 运行时不扫描业务 cwd 的 `.env`，只按 `ZENTAO_CONFIG_FILE` → 代码根 `.env`
  → Home config 选择一个配置文件；不在多个文件之间补字段。
- `ZENTAO_BASE_URL / ZENTAO_ACCOUNT / ZENTAO_PASSWORD` 环境变量覆盖所选文件，
  但不改变文件选择；显式配置不存在时失败。
- Token 通过 API v2 登录取得，不写回配置文件，不进入日志、错误详情、测试快照
  或文档示例。输出层继续递归脱敏 password/token/Authorization/Cookie 类字段。
- 配置文件目标权限为 `0600`，用户 runtime 根目录、cache、tmp 目录目标权限为
  `0700`；setup 通过交互式提示读取密码，不把 password 放入命令行。

## 短期 Token cache

为减少多个 Skill/CLI 进程重复登录，允许把 Token 临时写入当前 scope：

```text
project: <repo>/.tmp/zentao/auth/token-<scope>.json
user:    ~/.zentao-ai-assistant/cache/auth/token-<scope>.json
```

安全合同：

- scope 由 base URL + account 哈希得到；缓存正文只包含站点、账号、缓存时间和 Token，不含密码。
- 默认本地 TTL 8 小时；过期或损坏文件删除后重新登录。
- POSIX 目录 `0700`、文件 `0600`；项目 `.tmp/` 和用户 runtime `tmp/` 均为临时目录。
- 明确 HTTP 401 表示当前 Token 被服务器拒绝：清理旧缓存、重新登录，并重放该次被认证层拒绝的请求一次。
- 网络超时、连接中断或 5xx 不得借 Token cache 扩大写操作重试。

## 高层 Skill 数据

统计/个人/项目管理在 `--cache-data` 时可以把大批量中间 JSON 放到当前 scope：
project 为 `.tmp/zentao/<skill>/`，user 为
`~/.zentao-ai-assistant/tmp/zentao/<skill>/`。这些数据是临时运行材料，不得作为
长期数据库、兼容性证据或新的秘密配置系统。

## 对象资源下载

`resource fetch` 继续只获取对象附件区和富文本发现的同源资源，流式保存到当前
scope 的 trusted temp root：project 为 `.tmp/zentao-resources/`，user 为
`~/.zentao-ai-assistant/tmp/zentao-resources/`，并保持逐跳同源校验、文件名清洗、
符号链接/路径逃逸拒绝和 `.part` 清理。trusted temp root 随 scope 变化，但安全
强度不变。

## Plugin cache 边界

Claude/Codex Plugin cache 是可替换的代码目录，不是配置、Token 或持久数据目录。
宿主升级/重装可以替换 cache 副本，但不得要求把 `.env`、password、Token 或
认证 Header 写入其中；user runtime 始终位于 `~/.zentao-ai-assistant/`。

## Bug resolver 读取与写前复查

- `zentao-bug-resolver` 的 `select`、`snapshot`、`compare` 脚本只做确定性读取和比较，统一借 `zentao_skill.public`；不直连 HTTP，不 import `internal/**`，不执行 ZenTao lifecycle，也不写业务仓库。
- `compare` 是写前只读并发复查：`changed=true`、比较失败或关键事实不可安全比较时必须阻止写入。它不是 CAS、ETag、锁或强一致保证；`changed=false` 不代表对象已被保留或随后写入必然安全。
- Agent 只有在当前用户明确 R2 授权、证据分类/最小修复/真实验证/diff 审阅和 compare 门槛均通过后，才可调用基础 `zentao` CLI 一次执行 `bug resolve`，随后显式 snapshot/view 回读。不得通过 facade、私有接口或替代 lifecycle endpoint 写入，也不得把一次 R2 resolve 自动扩展为 close、activate、delete 或下一 Bug。

## 写入与结果不确定

POST/PUT/DELETE 网络失败不自动重试。写请求可能已执行但无法确认时返回 `UNKNOWN_WRITE_RESULT`；不自动 GET 或重放。R3 delete 继续要求 `--yes`。

resolver 继承基础 CLI 的认证和写入合同：401 只允许认证层清理缓存、重新登录并重放该次被拒绝请求一次；resolver workflow 不增加循环重试。出现 `UNKNOWN_WRITE_RESULT` 时绝不重试原 resolve，只读回读确认，无法证明预期状态则保持 unknown/blocked。

## 高层 Skill 写入边界

`zentao_skill.public` 程序化 facade 只读。任何高层 Skill 需要修改 ZenTao 数据时，必须回到 `zentao` CLI，以保留生命周期校验、delete `--yes` 和稳定错误合同。resolver 的一次 R2 resolve 只能走该基础 CLI；仓库不为此引入 MCP、第三方运行时依赖或新的 HTTP 通道。
