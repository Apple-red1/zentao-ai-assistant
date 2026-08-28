---
name: zentao-batch-export
description: Use when users want to export, package, or download complete data and resources for multiple ZenTao objects into one ZIP. Trigger on multi-object export/package/download intent; ordinary single-object view/query stays in zentao.
---

# 禅道批量资料导出（zentao-batch-export）

用于把多个 ZenTao 对象的完整 `view` 数据、附件和富文本关联资源整理到同一个 ZIP，便于下载、移交或后续 AI 分析。

## 触发边界

应触发：

- “把这几个禅道问题打包下载”；
- “导出 `bug:123`、`story:456`”；
- “把这些 Bug 的完整资料和附件打成 ZIP”；
- “批量下载这些任务/需求/工单”；
- “把多个 ZenTao 对象一起导出”。

不应触发：

- 单独“查看 Bug 123 / Task 456”——使用基础 `zentao`；
- 数量、分布、汇总、范围比较——使用 `zentao-statistics`；
- Bug 根因、修复或 resolve——使用 `zentao-bug-resolver`；
- 修改、删除、生命周期写入——回到基础 `zentao` 的明确写操作合同。

## 支持对象

首版支持当前同时具备正式 `view` 与 `resource fetch` 的 13 种 canonical 类型：

`bug / epic / execution / feedback / product / product-plan / program / requirement / story / task / test-case / ticket / user`

输入必须显式携带 `type + id`，禁止只传裸 ID 后猜测类型：

```text
bug:123
story:78
product-plan:67
test-case:89
```

## 调用

```bash
python skills/zentao-batch-export/scripts/zentao_batch_export.py \
  bug:123 story:78 task:90 \
  --json
```

脚本按 `type + id` 去重并保持首次出现顺序。输入格式、对象类型或 ID 非法属于调用错误，会在开始导出前返回明确错误。

## 输出合同

聊天回复中展示 Bug ID 时，编号本身必须可点击；回复前读取并遵守[共享 Bug 展示规则](../zentao/references/bug-display.md)。ZIP 内 `content.md` 使用可读 Markdown 展示完整字段；已成功归档的资源引用改为对象目录下的相对路径，下面的机器输出合同仍保持不变。

每个对象保留一个完整 `content.md`，其中以 Markdown 展示该对象 `view --json` 返回的全部字段，不挑选或裁剪字段；关联附件与富文本资源全部尝试归档到该对象的 `resources/`。富文本中已成功复制的图片和文件链接指向 `resources/<file>`，解压后可直接使用。

对 `bug` 和 `story`，批量导出会在调用基础 `resource fetch` 时显式包含已验证的评论资源：
Bug 包含评论普通附件和评论内嵌图片，Story 包含评论普通附件。其它对象只使用默认的
对象附件区/正文资源范围，不扫描评论 action；这不会新增 API endpoint。

ZIP 内部结构固定为：

```text
manifest.json
objects/
  <type>/
    <id>/
      content.md
      resources/
```

`manifest.json` 和 CLI 的 `--json` 输出继续使用机器可读 JSON；不额外生成与 `content.md` 重复的 `data.json`。只有未来出现 Markdown 无法无损承载的真实结构化数据时，才基于证据扩展格式。

`manifest.json` 只承担索引、完整性和失败记录，不复制标题、状态、负责人等业务字段：

```json
{
  "schema_version": 1,
  "complete": false,
  "requested_count": 2,
  "exported_count": 2,
  "objects": [
    {
      "type": "bug",
      "id": 123,
      "path": "objects/bug/123",
      "complete": false,
      "resource_count": 4,
      "failures": [
        {
          "stage": "resource_download",
          "resource": "screenshot.png",
          "code": "API_ERROR",
          "reason": "完整错误原因"
        }
      ]
    }
  ]
}
```

## 失败语义

- 单个对象详情、附件或富文本资源失败，不阻断后续对象；
- 已成功取得的内容全部保留，最终仍生成 ZIP；
- 包级与对象级 `complete` 必须如实标记；
- 失败项必须保留处理阶段、对象归属、资源（适用时）、错误码、完整原因和基础能力返回的详细信息；
- 资源复制前会再次拒绝空文件和明显的 HTML 登录/错误页；这类资源不得计入
  `resource_count`，对象和 ZIP 必须保持 `complete=false`；
- 禁止吞错、自动重试或把不完整资料写成完整。

## 落盘位置

脚本只使用当前 runtime scope 的受控临时目录，不接受任意输出路径：

```text
project: <repo>/.tmp/zentao/zentao-batch-export/<run-id>/
user:    ~/.zentao-ai-assistant/tmp/zentao/zentao-batch-export/<run-id>/
```

单次任务结构：

```text
<run-dir>/
├── zentao-export-<YYYYMMDD-HHMMSS>-<short-run-id>.zip
└── staging/
    ├── manifest.json
    └── objects/...
```

最终 ZIP 使用动态文件名，避免多次导出互相覆盖；文件名不拼接对象标题或其它业务内容。

## 架构与安全

- 批量解析、去重、逐对象编排、Markdown、manifest、失败汇总与 ZIP 打包均位于本 Skill 的 `scripts/`；
- 单对象详情继续调用基础 `zentao <type> view <id> --json`；
- 附件与富文本资源继续调用基础 `zentao resource fetch`，不复制资源发现、同源校验或下载逻辑；
- 只读，不执行 create/edit/lifecycle/delete；
- 不直连 ZenTao HTTP，不 import `zentao_skill.internal.*`；
- 资源只从基础 `resource fetch` 返回的当前 runtime `zentao-resources` 受控目录复制到本次 staging；拒绝符号链接和目录逃逸；
- 运行时和测试仅使用 Python 3.11+ 标准库。
