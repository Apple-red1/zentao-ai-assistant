---
name: zentao-personal
description: Use when users ask about their own or a specified person's ZenTao workload, pending work, priorities, overdue tasks, or work-summary material.
---

# 禅道个人工作（zentao-personal）

围绕“我/某个人在禅道上有什么事情要处理”聚合多个资源，并输出可复核的个人工作事实。

## 能力

- `overview`：个人工作概览、开放事项和风险项。
- `worklist`：按逾期、Severity 1 Bug、P1等事实排序的待处理清单。
- `brief`：适合作为日报/周报素材的紧凑事实摘要。
- 第一版聚合 Bug、Task、Story、Requirement、Ticket、Feedback。

## 调用

```bash
python skills/zentao-personal/scripts/zentao_personal.py overview --json
python skills/zentao-personal/scripts/zentao_personal.py worklist --user alice --json
python skills/zentao-personal/scripts/zentao_personal.py brief --json
```

`--user` 支持 account / realname；重名时返回歧义，禁止猜测。需要保存中间数据时使用 `--cache-data`。

## 规则

- 聊天回复中展示 Bug ID 时，编号本身必须可点击；回复前读取并遵守[共享 Bug 展示规则](../zentao/references/bug-display.md)。
- 默认只读。
- 个人报告是事实整理，不把工作量直接解释成绩效评价。
- 优先级建议必须能追溯到 ZenTao 的 priority、severity、deadline、status 等字段。
- 组合查询允许部分成功，但必须保留 `partial_failures` 和 `complete`。
- 需要修改 ZenTao 时，切换到 `zentao` Skill 的明确写操作，不在本 Skill 内绕过授权合同。
