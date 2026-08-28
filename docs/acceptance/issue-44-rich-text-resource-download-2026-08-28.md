# Issue #44 富文本图片资源下载验收

## 真实环境

- 配置来源：仓库 `.env.me`，未记录账号、密码或 Token。
- 对象：生产 ZenTao Bug `3647`。
- 发现资源：`bug.steps` 中的旧式 `/index.php?m=file&f=read&t=png&fileID=7395` 图片地址。

## 验证结果

执行：

```bash
ZENTAO_CONFIG_FILE=.env.me python3 skills/zentao/scripts/zentao.py \
  resource fetch --object-type bug --object-id 3647 --json
```

结果为成功，`partial_failures` 为空，资源输出保留原始 `file/read` source：

```json
{
  "file_name": "image.png",
  "content_type": "application/octet-stream",
  "size": 169052,
  "partial_failures": []
}
```

落盘文件校验：

- PNG 签名：通过（`89 50 4e 47 0d 0a 1a 0a`）。
- SHA-256：`bd5e7980bcfaa14dda5a0b7ba8139dba749171cf175ea90e09550bec04bdc1a2`。

实现只对富文本中的旧式图片请求把 `f=read` 改为同源 `f=download`；普通附件 URL 不改写。Fake E2E 测试同时断言了两类资源实际使用的查询参数。
