---
name: zentao-bug-board
description: Use when users want a manually generated, Project- or Product-wide 16:00 ZenTao Bug review board showing today's fixes, next statutory workday noon deadlines, overdue bugs, new bugs, and resolved bugs awaiting test verification. Resolve a named target across both Project and Product.
---

# 16:00 Bug 评审表

用户指定一个 ZenTao Project 或 Product 后，读取该范围所有可见 Bug，生成最新的只读待处理表。适用于“看今天 16 点 Bug 过会表”“这个项目今天/下个工作日要修哪些 Bug”“开发已解决、测试尚未验证的有哪些”。口语中的“项目”不等于 ZenTao 的 Project 资源；例如“WebHub-独立站营销智能体项目”实际为 Product 15，应该按 Product 读取。团队日报、个人待办和 Bug 生命周期操作分别交给其它 Skill。

## 调用

```bash
python skills/zentao-bug-board/scripts/zentao_bug_board.py --project 12
python skills/zentao-bug-board/scripts/zentao_bug_board.py --project 12 --json
python skills/zentao-bug-board/scripts/zentao_bug_board.py --product 15
python skills/zentao-bug-board/scripts/zentao_bug_board.py --name 'WebHub-独立站营销智能体项目'
```

用户给出名称时，提取目标名称并优先传 `--name`。脚本完整分页查询 Project 与 Product 目录，先按完整名称精确匹配；若名称末尾是口语后缀“项目”且无精确匹配，再去掉该后缀精确匹配。跨类型重名、未找到或目录不完整时报告明确原因，不猜测相近名称或 ID。已确认类型和 ID 时可用 `--project` 或 `--product`。用户未指定目标时先请其指定。

## 结果口径

- 业务时区固定为 `Asia/Shanghai`。每次手动查询当前快照，不自动定时推送、不保存历史快照。
- `status=closed` 不出现在任何行动清单，也不默认展示关闭数量；`resolved` 进入“已解决待测试验证”，分别展示 `resolvedBy` 和当前 `assignedTo`；`active` 使用当前 `assignedTo` 作为研发负责人。
- 当天 16:00:00 及之后创建且仍 `active` 的 Bug 只在“16:00 后新增”；下一日按当前 `pri` 重新分类。用户已确认本实例 `pri=0` 为 P0，`pri=1..4` 对应 P1..P4。
- P0～P2 在本轮 16:00 前提出：今天下班前；P3/P4：下一个中国法定工作日 12:00 前。超过可核定要求且仍 `active` 的项进入“历史未完成”。不假定具体下班钟点；12:00:00 起视为超过中午期限。
- 工作日日历只包含已核验的国务院 2025、2026 年放假及调休通知，详见[日历来源](references/calendar.md)。涉及未核验年份时进入“待核定”，不按固定周一到周五猜测。
- 历史完成要求按当前优先级及原创建时刻推算。列表数据未证明历史优先级是否变化，输出会标明这一限制；若真实数据缺少状态、优先级、精确创建时刻等关键字段，进入“待核定”。
- 保留完整分页失败、重复 ID 冲突、链接失败和数据异常；`complete=false` 不能被描述成目标范围全部待办或零 Bug。评审表按目标 Project/Product 的所有可见 Bug 生成；“我的团队 Bug/日报”按配置的团队成员过滤，属于 `zentao-personal`，两者数量不一定相同。聊天中展示 Bug ID 时遵守[共享 Bug 展示规则](../zentao/references/bug-display.md)。

## 边界

脚本仅通过 `zentao_skill.public` 读取 Project/Product/Bug 及生成 Bug URL，不直接访问 HTTP 或 `internal/**`，不修改 Bug、不执行 resolve/close/assign，不新增 API endpoint。`--json` 保留原始 ID 和机器字段，范围分别位于 `project` 或 `product`；默认 Markdown 表中的 ID 可点击。
