# 本地配置

`zentao` Skill 只读取项目根目录 `.env` 和同名环境变量，不依赖 YAML、keyring、独立 token 文件或凭据数据库。

## 最小配置

复制 `.env.example` 为 `.env`：

```dotenv
ZENTAO_BASE_URL=https://zentao.example.com
ZENTAO_ACCOUNT=your-account
ZENTAO_PASSWORD=your-password
```

环境变量优先于 `.env` 中的同名值。脚本通过自身路径定位项目根目录，因此可以从任意当前工作目录执行。

`setup` 使用受限且对称的 dotenv 编码：双引号值中的 `\\` 与 `\"` 会在读取时还原，
密码不会被统一 `.strip()`，因此引号、反斜杠、Unicode、`#`、`=` 以及首尾空格都能
无损往返。NUL 和换行无法表示为单行 `.env` 值，会在写入前明确拒绝。

`.env` 与 `.env.*` 被 Git 忽略，`.env.example` 明确保留。请勿提交真实站点地址、账号、密码、Token、Cookie 或 Authorization Header。

## 登录与 Token

业务请求前通过 `POST /api.php/v2/users/login` 获取 Token。Token 只保存在当前 Python 进程内存中，不写回 `.env`，也不持久化到其他文件。

可以执行：

```bash
python skills/zentao/scripts/zentao.py doctor --json
```

验证当前配置和 API v2 登录是否可用。
