# Issue #44 批量导出 Markdown 内容验收

## 真实环境

- 配置来源：仓库 `.env.me`，未记录账号、密码或 Token。
- 对象：生产 ZenTao Bug `3641`。
- 原始富文本图片：`/index.php?m=file&f=read&t=png&fileID=7382`。

## 验证命令

```bash
ZENTAO_CONFIG_FILE=.env.me python3 skills/zentao-batch-export/scripts/zentao_batch_export.py \
  bug:3641 --json
```

本次运行 ID：`20260828-055057-beddfd50`。

## 验证结果

- `complete=true`、`requested_count=1`、`exported_count=1`。
- ZIP 包含 `objects/bug/3641/content.md` 和 1 个 PNG 资源：
  `objects/bug/3641/resources/d419f059-2714-4dae-9e8b-8266f22f9585-3.png`。
- `content.md` 使用 Markdown 字段格式，不包含 `json` fenced code block。
- `steps` 已转换为：

  ```markdown
  ![d419f059-2714-4dae-9e8b-8266f22f9585-3.png](<resources/d419f059-2714-4dae-9e8b-8266f22f9585-3.png>)
  ```

- `manifest.json` 仍保持机器可读 JSON，并记录 `resource_count=1`、空 `failures`。
- 未成功归档的历史图片占位内容只显示为未归档提示，不生成外部 Markdown 图片请求。
