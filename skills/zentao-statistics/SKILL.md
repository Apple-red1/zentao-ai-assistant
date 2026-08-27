---
name: zentao-statistics
description: Use when users ask for deterministic ZenTao counts, distributions, summaries, or comparisons across supported project-management resources.
---

# 禅道统计（zentao-statistics）

用于把 ZenTao 列表数据转换为可复现的统计结果。数字、分组、去重和分页由脚本计算，AI 负责解释。

## 能力

- `summary`：一个范围内的资源统计；未传 `--browse` 时默认使用该资源的全量 browse 语义。
- `compare`：多个同类范围的并列比较，同一次 compare 只接受同一种 scope 类型。
- 第一版支持 `bug / task / story / requirement / test-case / test-task / ticket / feedback`。
- 自动读取完整分页；结果保留 `complete`、`partial_failures`、`duplicates_removed`。
- Task 支持 deadline 事实分类；Bug 支持状态、负责人、优先级、严重程度等实际存在字段的统计。

## 调用

```bash
python skills/zentao-statistics/scripts/zentao_statistics.py summary bug --product 1 --json
python skills/zentao-statistics/scripts/zentao_statistics.py compare bug --scope product:1 --scope product:2 --json
```

需要保留大批量中间数据时增加 `--cache-data`；数据落到当前 runtime scope：
project 为 `<repo>/.tmp/zentao/statistics/`，user 为
`~/.zentao-ai-assistant/tmp/zentao/statistics/`。

## 规则

- 只读，不执行 create/edit/lifecycle/delete。
- 不直接拼 ZenTao URL；底层通过 `zentao` 的 programmatic public facade。
- 不根据当前快照伪造历史趋势。
- `complete=false` 或存在 `partial_failures` 时，回答必须明确统计并非完整事实。
- 字段缺失时不臆造该维度；后续维度可随真实 API 证据迭代。
- `--cache-data` 生成的 JSON 只是临时运行材料，不是长期事实源或审计数据库。
