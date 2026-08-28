# file · ZenTao API v2

参数细节以 CLI `--help` 为运行时事实；本页只做领域导航。

| Endpoint | API | CLI | 风险 | 用途 |
|---|---|---|---|---|
| `file.upload` | `POST` `/api.php/v2/files` | `file upload` | R1 | 上传附件 |
| `file.edit` | `PUT` `/api.php/v2/files/{fileID}` | `file edit` | R1 | 修改附件名称 |
| `file.delete` | `DELETE` `/api.php/v2/files/{fileID}` | `file delete` | R3 | 删除附件 |

风险：R0 读取；R1 普通写；R2 生命周期；R3 删除。R3 只有当前用户明确要求删除具体对象时才允许执行，并必须给 CLI 传 `--yes`。

## 21.7.8 上传兼容路径

官方 `POST /api.php/v2/files` 在目标 ZenTao 21.7.8 实例上会返回空响应，不能把
HTTP 200 当作上传成功。`file upload --object-type bug` 遇到这个明确的空响应时，
CLI 会先通过 `bug view` 回读：如果附件名和大小已经匹配，则直接返回已落库的附件，
不重复写入；确认未落库后，才使用同一配置源的网页登录态，向固定的
`/index.php?m=bug&f=edit&bugID=<id>` 提交 `files[]` 页面表单，并再次通过 `bug view`
确认附件 ID、文件名和大小。

该路径是基础 Skill 内部的 21.7.8 兼容实现，不接受调用方传入任意页面 URL，也不使用
浏览器自动化；`story`、`task` 和 `testcase` 仍保持原 v2 行为。页面写入发生异常时只做
一次只读回读，未确认时返回 `UNKNOWN_WRITE_RESULT`，不会盲目重试。
