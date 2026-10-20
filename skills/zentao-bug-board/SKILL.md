---
name: zentao-bug-board
description: Use when users want a manually generated, project-wide 16:00 ZenTao Bug review board showing today's fixes, next statutory workday noon deadlines, overdue bugs, new bugs, and resolved bugs awaiting test verification.
---

# 16:00 Bug 评审表

用户指定一个 ZenTao Project 后，读取该项目所有可见 Bug，生成最新的只读待处理表。适用于“看今天 16 点 Bug 过会表”“这个项目今天/下个工作日要修哪些 Bug”“开发已解决、测试尚未验证的有哪些”。团队日报、个人待办和 Bug 生命周期操作分别交给其它 Skill。

## 调用

```bash
python skills/zentao-bug-board/scripts/zentao_bug_board.py --project 12
python skills/zentao-bug-board/scripts/zentao_bug_board.py --project 12 --json
```

`--project` 必须是已唯一确认的 Project ID。用户只给名称时，先通过基础只读 `project list` 完整分页核对名称与 ID；重名、缺失或查询不完整时请用户明确项目，不猜 ID。用户未指定项目时先请其指定。

## 结果口径

- 业务时区固定为 `Asia/Shanghai`。每次手动查询当前快照，不自动定时推送、不保存历史快照。
- `status=closed` 不出现在任何行动清单，也不默认展示关闭数量；`resolved` 进入“已解决待测试验证”，分别展示 `resolvedBy` 和当前 `assignedTo`；`active` 使用当前 `assignedTo` 作为研发负责人。
- 当天 16:00:00 及之后创建且仍 `active` 的 Bug 只在“16:00 后新增”；下一日按当前 `pri` 重新分类。用户已确认本实例 `pri=0` 为 P0，`pri=1..4` 对应 P1..P4。
- P0～P2 在本轮 16:00 前提出：今天下班前；P3/P4：下一个中国法定工作日 12:00 前。超过可核定要求且仍 `active` 的项进入“历史未完成”。不假定具体下班钟点；12:00:00 起视为超过中午期限。
- 工作日日历只包含已核验的国务院 2025、2026 年放假及调休通知，详见[日历来源](references/calendar.md)。涉及未核验年份时进入“待核定”，不按固定周一到周五猜测。
- 历史完成要求按当前优先级及原创建时刻推算。列表数据未证明历史优先级是否变化，输出会标明这一限制；若真实数据缺少状态、优先级、精确创建时刻等关键字段，进入“待核定”。
- 保留完整分页失败、重复 ID 冲突、链接失败和数据异常；`complete=false` 不能被描述成项目全部待办或零 Bug。聊天中展示 Bug ID 时遵守[共享 Bug 展示规则](../zentao/references/bug-display.md)。

## 边界

脚本仅通过 `zentao_skill.public` 读取 Project/Bug 及生成 Bug URL，不直接访问 HTTP 或 `internal/**`，不修改 Bug、不执行 resolve/close/assign，不新增 API endpoint。`--json` 保留原始 ID 和机器字段；默认 Markdown 表中的 ID 可点击。
