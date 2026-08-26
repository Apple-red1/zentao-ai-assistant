# zentao programmatic public facade

仓库内其他高层 Skill 需要在一个 Python 进程内复用 ZenTao Session 时，使用：

```python
from zentao_skill.public import ZentaoClient
```

公开对象：

- `ZentaoClient.call(resource, action, **kwargs)`：调用 facade 白名单中的明确只读 Service 操作；
- `ZentaoClient.list_page(...)`：读取一个列表页；
- `ZentaoClient.list_all(...)`：按 pager 读取完整分页；重复页/无进展时返回 `PAGINATION_STALLED`，不误报完整；
- `ZentaoClient.view(...)`：读取单对象；
- `ZentaoClient.account`：当前配置账号。

该 facade 只复用现有 Service/API adapter，不生成动态 HTTP endpoint。高层 Skill 禁止直接 import `internal/zentao` 或 `internal/http`。

Token 默认短期缓存在项目 `.tmp/zentao/auth/`，用于多个独立 Skill/CLI 进程减少重复登录；缓存按 base URL + account 隔离，POSIX 文件为 `0600`、目录为 `0700`，本地 TTL 为 8 小时。服务端提前失效时，收到明确 401 后清理旧缓存、重新登录并重放该次已被认证层拒绝的请求一次。

## 写操作边界

程序化 facade 只读：只提供 list/view 等读取能力，不暴露 create/edit/lifecycle/delete。需要写入时继续走 `zentao` CLI，让 CLI 的参数、风险和 `--yes` 等安全合同保持生效。
