
# 架构

```text
用户 / AI
  -> skills/zentao/SKILL.md
  -> scripts/zentao.py
  -> cli/<resource>/commands.py
  -> services/<resource>/service.py
  -> internal/zentao/<resource>.py
  -> internal/zentao/session.py
  -> internal/http/client.py
  -> ZenTao API v2
```

依赖只向下。CLI/Services 不拼接 API URL，HTTP 层不知道领域资源。领域 endpoint 在 Internal 层显式实现，`endpoints.json` 不参与运行时路由。
