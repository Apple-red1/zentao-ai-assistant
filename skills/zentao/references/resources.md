# resource · ZenTao 对象关联资源获取

`resource` 是 zentao Skill 的只读增强能力，不计入官方 API v2 的 120 个 endpoint。它用于获取对象附件区和富文本中实际引用的资源文件。

## 命令

```bash
python skills/zentao/scripts/zentao.py resource fetch \
  --object-type bug \
  --object-id 123 \
  --json
```

当前可获取具有官方 `view` 能力的对象类型：`bug`、`epic`、`execution`、`feedback`、`product`、`product-plan`、`program`、`requirement`、`story`、`task`、`test-case`、`ticket`、`user`。

## 发现范围

只从当前对象详情的两个来源发现资源：

1. `files` 等附件区元数据；
2. 富文本中的内联/链接资源，包括图片、音视频、嵌入对象、CSS `url(...)` 和明显的文件下载链接。

不扫描页面、不抓取全站资源，也不接受调用方传入任意 URL；对象详情中的
`actions`、`history`、`diff` 审计历史字段不作为当前资源来源扫描。

## 下载与本地文件

- 用户明确要求获取/分析对象资源时，发现到的全部资源都会尝试下载，不按图片类型筛选；
- HTTP 资源必须与 `ZENTAO_BASE_URL` 同源，同源重定向允许继续，跨源重定向拒绝；
- Token 只会发送给通过同源校验的资源请求；
- HTTP 文件以流式方式写入当前 runtime scope 的资源目录：project 为
  `<project-root>/.tmp/zentao-resources/<object-type>-<object-id>/`，user 为
  `~/.zentao-ai-assistant/tmp/zentao-resources/<object-type>-<object-id>/`；
- HTTP 200 不等于资源成功：空响应、疑似登录页/HTML 错误页，以及响应 MIME 与
  资源类型提示冲突的文件，会以 `RESOURCE_CONTENT_INVALID` 记入
  `partial_failures`，不会进入成功资源列表；
- 旧式 `/index.php?...fileID=...` URL 的文件名优先使用资源 ID 和类型提示生成，
  不会直接落盘为无语义的 `index.php`；
- 项目 `.tmp/` 与用户 runtime `tmp/` 均用于临时数据，资源默认不自动清理；
- 同名文件自动生成 `-2`、`-3` 等唯一名称，不覆盖已有文件；
- `data:` 内联资源直接从对象内容解码到同一临时目录。

资源落盘目录由当前 runtime scope 决定，不接受调用方用任意路径覆盖。目录及其
父级必须是受保护的普通目录；拒绝符号链接和逃逸到可信临时根之外的路径。
HTTP 请求继续只允许与 `ZENTAO_BASE_URL` 同源，逐跳校验同源重定向，跨源重定向
拒绝，并且只向通过同源校验的请求发送 Token。

## 结果语义

成功项返回 `source`、`origin`、`field`、`file_name`、`content_type`、`size`、`local_path`。

- 至少一个资源下载成功：exit `0`，失败项保留在 `partial_failures`；
- 对象没有资源：exit `0`，`resources=[]`；
- 发现了资源但全部失败：exit `1`，错误码 `RESOURCE_FETCH_FAILED`；
- 跨站资源或跨源重定向：失败项错误码 `RESOURCE_SECURITY_ERROR`。

`view` 命令仍只读取对象详情，不会自动下载资源。需要同时理解文本和附件时，由 Skill 显式组合 `view` 与 `resource fetch`。
