# 安全模型

## 长期秘密与认证

- `.env` 保存 `ZENTAO_BASE_URL / ZENTAO_ACCOUNT / ZENTAO_PASSWORD` 并被 Git 忽略；`.env.example` 不含真实秘密。
- Token 通过 API v2 登录取得，不写回 `.env`，不进入日志、错误详情、测试快照或文档示例。
- 输出层继续递归脱敏 password/token/Authorization/Cookie 类字段。

## 短期 Token cache

为减少多个 Skill/CLI 进程重复登录，允许把 Token 临时写入：

```text
.tmp/zentao/auth/token-<scope>.json
```

安全合同：

- scope 由 base URL + account 哈希得到；缓存正文只包含站点、账号、缓存时间和 Token，不含密码。
- 默认本地 TTL 8 小时；过期或损坏文件删除后重新登录。
- POSIX 目录 `0700`、文件 `0600`；`.tmp/` 被 Git 忽略。
- 明确 HTTP 401 表示当前 Token 被服务器拒绝：清理旧缓存、重新登录，并重放该次被认证层拒绝的请求一次。
- 网络超时、连接中断或 5xx 不得借 Token cache 扩大写操作重试。

## 高层 Skill 数据

统计/个人/项目管理在 `--cache-data` 时可以把大批量中间 JSON 放到 `.tmp/zentao/<skill>/`。这些数据是临时运行材料，不得作为长期数据库、兼容性证据或新的秘密配置系统。

## 对象资源下载

`resource fetch` 继续只获取对象附件区和富文本发现的同源资源，流式保存到 `.tmp/zentao-resources/`，并保持逐跳同源校验、文件名清洗和 `.part` 清理。

## 写入与结果不确定

POST/PUT/DELETE 网络失败不自动重试。写请求可能已执行但无法确认时返回 `UNKNOWN_WRITE_RESULT`；不自动 GET 或重放。R3 delete 继续要求 `--yes`。

## 高层 Skill 写入边界

`zentao_skill.public` 程序化 facade 只读。任何高层 Skill 需要修改 ZenTao 数据时，必须回到 `zentao` CLI，以保留生命周期校验、delete `--yes` 和稳定错误合同。
