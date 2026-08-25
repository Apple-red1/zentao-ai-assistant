# 架构

当前合同入口：[`docs/current-contract.md`](current-contract.md)。本仓库是面向 AI 的 ZenTao 项目管理 Skill 集合。

## API 基础层

```text
用户 / AI
  -> skills/zentao/SKILL.md
  -> scripts/zentao.py
  -> cli/<resource>
  -> services/<resource>
  -> internal/zentao/<resource>.py
  -> internal/zentao/session.py
  -> internal/http/client.py
  -> ZenTao API v2
```

API endpoint 保持显式实现，`endpoints.json` 不参与运行时路由。

## 高层 Skill

```text
zentao-statistics ---------┐
zentao-personal -----------+--> skills/_shared/zentao
zentao-project-management -┘        |
                                     v
                              zentao_skill.public
                                     |
                                     v
                               existing Services
                                     |
                                     v
                               ZenTao API v2
```

`zentao_skill.public` 是仓库内部稳定 programmatic facade，用于在一个 Python 进程内复用 Session 和完整分页。高层 Skill 禁止直接访问 `internal/zentao` / `internal/http`。

## 临时运行数据

```text
.tmp/zentao/auth/               # 短期 Token cache
.tmp/zentao/statistics/         # 可选统计中间数据
.tmp/zentao/personal/           # 可选个人聚合中间数据
.tmp/zentao/project-management/ # 可选项目聚合中间数据
.tmp/zentao-resources/          # 对象附件/富文本资源
```

所有 `.tmp` 数据都被 Git 忽略。Token cache 是性能优化，不是新的凭据事实源；失效时回到 `/users/login`。

## 程序化 facade 安全边界

`zentao_skill.public` 是仓库内高层 Skill 的只读 facade，只暴露 list/view 类读取。写操作仍由 `zentao` CLI 承担，避免高层 Skill 绕过 delete `--yes` 等 CLI 安全合同。
