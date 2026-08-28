---
name: zentao-project-management
description: Use when users ask for ZenTao project or execution overview, health, risks, blockers, or workload distribution across related work items.
---

# 禅道项目管理（zentao-project-management）

围绕 Project / Execution 聚合需求、任务、Bug、测试和构建数据，形成项目管理视角的事实报告。

## 能力

- `overview`：资源总量、开放事项和状态分布。
- `health`：事实摘要 + 风险信号。
- `risks`：Severity 1 / P1 Bug、逾期任务、无负责人事项、数据不完整等风险。
- `workload`：开放事项按负责人和资源类型分布。

## 调用

```bash
python skills/zentao-project-management/scripts/zentao_project_management.py health --project 12 --json
python skills/zentao-project-management/scripts/zentao_project_management.py risks --execution 18 --json
python skills/zentao-project-management/scripts/zentao_project_management.py workload --project 12 --json
```

需要保留中间聚合数据时使用 `--cache-data`；文件位于当前 runtime scope：
project 为 `<repo>/.tmp/zentao/project-management/`，user 为
`~/.zentao-ai-assistant/tmp/zentao/project-management/`。

## 规则

- 项目报告中的对象链接先按[对象 Web URL 证据合同](../zentao/references/web-urls.md)核对来源；不得仅凭 ID 或历史示例拼接链接。没有可靠证据时返回对象 ID，并说明“页面 URL：当前能力无法可靠生成/尚未验证”。
- 默认只读。
- 默认不生成数值“健康分”；没有明确规则时只报告事实和风险信号。
- workload 只表达事项分布，不自动推导人员绩效。
- `complete=false` 或有 `partial_failures` 时必须明确数据边界。
- 高层分析不直接访问 ZenTao HTTP/Internal；数据统一来自 `zentao` programmatic public facade。
- `--cache-data` 生成的 JSON 只是临时运行材料，不是长期事实源或审计数据库。
