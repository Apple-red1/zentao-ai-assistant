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

## 21.7.8 Bug 附件页面兼容上传

目标实例的 v2 文件上传空响应只能视为结果不确定。基础层先用 Bug 详情回读；只有未
找到同名同大小附件时，才使用同一配置源的账号密码建立内存 Cookie 会话，并向固定的
Bug 编辑页面提交 `files[]`。页面响应本身不作为成功依据，必须再用 API 详情确认附件
ID、文件名和大小。页面写入异常只允许一次只读回读；无法确认时返回
`UNKNOWN_WRITE_RESULT`，不自动重复提交。页面客户端只接受仓库内部构造的同源路径，不
接受任意 URL，不把密码、Cookie 或页面响应写入日志/输出。

## 高层 Skill 数据

统计/个人/项目管理在 `--cache-data` 时可以把大批量中间 JSON 放到当前 scope：
project 为 `.tmp/zentao/<skill>/`，user 为
`~/.zentao-ai-assistant/tmp/zentao/<skill>/`。这些数据是临时运行材料，不得作为
长期数据库、兼容性证据或新的秘密配置系统。

## 批量资料导出

`zentao-batch-export` 只读复用基础 CLI：对象详情来自 `view`，资源来自 `resource fetch`。脚本不接受任意输出路径，project/user scope 分别只写入 `.tmp/zentao/zentao-batch-export/` 与 `~/.zentao-ai-assistant/tmp/zentao/zentao-batch-export/`。资源复制只接受基础资源目录 `zentao-resources` 下的普通文件，拒绝符号链接与目录逃逸；动态 ZIP 文件名不拼接对象标题或其它业务内容。部分失败通过 manifest 显式保留，不触发隐式重试。

## 对象资源下载

`resource fetch` 继续只获取对象附件区和富文本发现的同源资源，流式保存到当前
scope 的 trusted temp root：project 为 `.tmp/zentao-resources/`，user 为
`~/.zentao-ai-assistant/tmp/zentao-resources/`，并保持逐跳同源校验、文件名清洗、
符号链接/路径逃逸拒绝和 `.part` 清理。trusted temp root 随 scope 变化，但安全
强度不变。下载完成后还会拒绝空响应、明显的登录/错误 HTML 和资源提示 MIME
冲突；旧式文件页 URL 不直接使用 `index.php` 作为落盘名。

## Plugin cache 边界

Claude/Codex Plugin cache 是可替换的代码目录，不是配置、Token 或持久数据目录。
宿主升级/重装可以替换 cache 副本，但不得要求把 `.env`、password、Token 或
认证 Header 写入其中；user runtime 始终位于 `~/.zentao-ai-assistant/`。

## Bug resolver 读取与写前复查

- `zentao-bug-resolver` 的 `select`、`snapshot`、`compare` 脚本只做确定性读取和比较，统一借 `zentao_skill.public`；不直连 HTTP，不 import `internal/**`，不执行 ZenTao lifecycle，也不写业务仓库。
- `compare` 是写前只读并发复查：`changed=true`、比较失败或关键事实不可安全比较时必须阻止写入。它不是 CAS、ETag、锁或强一致保证；`changed=false` 不代表对象已被保留或随后写入必然安全。
- 普通证据流程的 Agent 只有在当前用户明确 R2 授权、证据分类/最小修复/真实验证/diff 审阅和 compare 门槛均通过后，才可调用基础 `zentao` CLI 一次执行 `bug resolve`，随后显式 snapshot/view 回读。不得通过 facade、私有接口或替代 lifecycle endpoint 写入，也不得把普通流程的一次 R2 resolve 自动扩展为 close、activate、delete 或下一 Bug。

## 人工确认解决的独立授权边界

`HUMAN_ATTESTED_RESOLVE` 只接受当前用户明确的已解决确认及唯一目标；该消息就是对应 Bug 的人工业务结论与 R2 授权。“帮我修复”、条件句或不确定表达不构成完成确认。此分支不读取业务仓库、提交、测试、diff、附件或 patch，不执行 select/snapshot/compare；普通证据门槛不适用。

每个 Bug 最小 pre-view 后，active 才允许一次基础 CLI fixed resolve 并显式回读；resolved/closed 零写入。默认显式 `--resolved-build trunk`，用户明确值覆盖；默认不传 assignee/resolved-date。自动 HUMAN-ATTESTED 备注只记录用户结论及本次版本参数，不编造验证或提交事实。

单 Bug 可由当前上下文唯一确定；多 Bug 请求只处理当前消息明确列出的 ID，按输入顺序去重、严格串行，不补入历史 pending 项。真实阻塞时不读取后续对象。包括 trunk 被拒绝在内的业务/权限错误必须如实反馈，不猜字段、不自动重试，不用 edit/close/activate 或私有接口绕过。`UNKNOWN_WRITE_RESULT` 停止整个队列，仅显式只读回读；即使回读为 resolved 也不自动继续，无法确认则保留 unknown。最小 view 不是 CAS/ETag/锁，不保证读写间无并发变化。

## 写入与结果不确定

POST/PUT/DELETE 网络失败不自动重试。写请求可能已执行但无法确认时返回 `UNKNOWN_WRITE_RESULT`；不自动 GET 或重放。R3 delete 继续要求 `--yes`。

resolver 继承基础 CLI 的认证和写入合同：401 只允许认证层清理缓存、重新登录并重放该次被拒绝请求一次；resolver workflow 不增加循环重试。出现 `UNKNOWN_WRITE_RESULT` 时绝不重试原 resolve，只读回读确认，无法证明预期状态则保持 unknown/blocked。

## 高层 Skill 写入边界

`zentao_skill.public` 程序化 facade 只读。任何高层 Skill 需要修改 ZenTao 数据时，必须回到 `zentao` CLI，以保留生命周期校验、delete `--yes` 和稳定错误合同。resolver 的一次 R2 resolve 只能走该基础 CLI；仓库不为此引入 MCP、第三方运行时依赖或新的 HTTP 通道。
