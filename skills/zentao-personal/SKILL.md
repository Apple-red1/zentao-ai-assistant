---
name: zentao-personal
description: Use for personal ZenTao workload, pending work, and summaries, or maintaining a personal default team and querying its Bug list or daily report.
---

# 禅道个人工作（zentao-personal）

围绕“我/某个人在禅道上有什么事情要处理”聚合多个资源，并输出可复核的个人工作事实。

## 能力

- `overview`：个人工作概览、开放事项和风险项。
- `worklist`：按逾期、Severity 1 Bug、P1等事实排序的待处理清单。
- `brief`：适合作为日报/周报素材的紧凑事实摘要。
- 第一版聚合 Bug、Task、Story、Requirement、Ticket、Feedback。
- 个人默认团队：查看、添加、移除、整体替换成员；团队 Bug 与团队日报共用本人及成员的未关闭 Bug 数据。

## 调用

```bash
python skills/zentao-personal/scripts/zentao_personal.py overview --json
python skills/zentao-personal/scripts/zentao_personal.py worklist --user alice --json
python skills/zentao-personal/scripts/zentao_personal.py brief --json
```

`--user` 支持 account / realname；重名时返回歧义，禁止猜测。需要保存中间数据时使用 `--cache-data`。

## 团队入口

用户要求“设置/查看我的团队”“查询团队的 Bug”“查询今日团队日报”时，读取
[团队合同](references/team.md)，使用本 Skill；Project / Execution 仅缩小本次
查询，不切换到项目团队成员发现，也不调用个人 `brief` 代替团队日报。

```bash
python skills/zentao-personal/scripts/zentao_personal.py team-add --member alice --member 张三 --json
python skills/zentao-personal/scripts/zentao_personal.py team-bugs --markdown
python skills/zentao-personal/scripts/zentao_personal.py team-brief --markdown
```

聊天优先直接保留脚本的四列表格、全部明细与完整性提示，不自行缩成重点项。
本人始终纳入；`active` 与 `resolved` 分区，排除 `closed`。今日表示当前快照，
不按创建/更新时间过滤。两种团队入口共用同一数据链路和排序器。

## 规则

- 聊天回复中展示 Bug ID 时，编号本身必须可点击；回复前读取并遵守[共享 Bug 展示规则](../zentao/references/bug-display.md)。
- ZenTao 数据只读；仅用户明确要求维护名单时写本机用户级团队配置，不修改 ZenTao 用户或 Bug。
- 个人报告是事实整理，不把工作量直接解释成绩效评价。
- 优先级建议必须能追溯到 ZenTao 的 priority、severity、deadline、status 等字段。
- 组合查询允许部分成功，但必须保留 `partial_failures` 和 `complete`。
- 需要修改 ZenTao 时，切换到 `zentao` Skill 的明确写操作，不在本 Skill 内绕过授权合同。
