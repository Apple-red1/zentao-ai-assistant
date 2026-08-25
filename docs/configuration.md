# 本地配置

长期连接配置只读取项目根 `.env` 和同名环境变量：

```dotenv
ZENTAO_BASE_URL=https://zentao.example.com
ZENTAO_ACCOUNT=your-account
ZENTAO_PASSWORD=your-password
```

环境变量优先于 `.env`。脚本按自身路径定位项目根目录。`.env` 使用受限、对称的 dotenv codec，并以安全原子写入保存；POSIX 目标权限为 `0600`。

`.env` 与 `.env.*` 被 Git 忽略，`.env.example` 明确保留。不得提交真实站点秘密。

## Token

业务请求通过 `POST /api.php/v2/users/login` 获取 Token。Token 不写入 `.env`。

为了让统计、个人和项目管理 Skill 的多个独立进程减少重复登录，Token 默认可以短期缓存在：

```text
.tmp/zentao/auth/
```

缓存按站点 + account 隔离，默认本地 TTL 8 小时；服务端若提前使 Token 失效，明确 401 会触发一次重新登录。缓存不保存密码，`.tmp/` 不提交。

`ZENTAO_TOKEN_CACHE_DIR` 和 `ZENTAO_TOKEN_CACHE_DISABLED=1` 是内部运行/测试覆盖开关，不属于长期连接配置事实源。
