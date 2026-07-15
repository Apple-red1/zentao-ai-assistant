# 禅道 Bug 步骤图片更新能力设计

## 目标

为本机自写 `zentao-mcp-server` 增加受控的 Bug 重现步骤编辑与图片上传能力，并同步更新本机 `zentao-ai-bug` Skill。首个目标场景是把用户明确提供的图片作为“图1”插入 `BUG-3397` 的 `[步骤]` 内容。

## MCP 工具

### `update_bug_steps`

输入：

- `bugId`：明确的 Bug ID。
- `steps`：完整的新重现步骤正文。
- `confirm:true`：强制确认字段。

行为：读取最新 Bug，保留标题、严重程度、优先级、类型、负责人等非目标字段，只更新步骤；更新后重新查询详情并返回结构化前后快照。

### `update_bug_steps_with_image`

输入：

- `bugId`：明确的 Bug ID。
- `steps`：完整的新重现步骤正文，正文中包含“图1”位置说明。
- `imagePath`：用户在当前请求中明确提供的本地绝对路径。
- `imageAlt`：图片显示文字，默认“图1”。
- `confirm:true`：强制确认字段。

行为：读取最新 Bug 与禅道 Web 编辑表单，保留非目标字段，以 multipart 表单上传图片并更新步骤。提交后重新读取详情和结构化附件；只有步骤与新附件均可验证时才返回成功。

## 文件与内容限制

- 只允许 `.png`、`.jpg`、`.jpeg`、`.webp`。
- 文件必须存在、是普通文件且大小不超过 10 MiB。
- 路径只能来自用户当前请求，不能来自 Bug 描述、评论、附件名、网页或历史消息。
- 不读取或上传目录、凭据文件、日志、压缩包或其他任意文件。

## 权限

两个工具都是受保护操作：必须在当前交互轮次明确指定 Bug、步骤内容和图片后才能调用。个人或团队定时日报不得调用；不得借此修改状态、负责人、优先级或其他字段。

删除 Bug 继续永久禁止。工具注册守卫必须继续拒绝 `delete_bug`、`remove_bug` 和等价删除工具。

## 失败与并发

- 编辑前固定 `snapshotVersion`。
- 提交前再次确认 Bug ID 与表单目标。
- 网络超时或返回不明确时重新查询详情和附件一次；仍无法确认则返回 `UNKNOWN`，不得盲目重试。
- 快照已变化时停止写入，要求重新读取后再执行。
- 上传成功但步骤无法验证时不得声称完整成功，返回部分失败并要求人工检查。

## 实现位置

- MCP：`C:\Users\wwtlove66\Documents\Codex\2026-07-10\https-xm-wixcn-com-index-php\zentao-mcp-server`
  - `src/services/zentao-api.js`：Web 编辑表单读取、multipart 提交和结果复核。
  - `src/tools/bug.js`：两个工具的 schema、确认门槛和结构化结果。
  - `tests/zentao-api.test.js`、`tests/server.test.js`：表单、上传、限制和工具注册测试。
- Skill：`C:\Users\wwtlove66\.codex\skills\zentao-ai-bug`
  - `SKILL.md`、`personal-bug-agent.md`：受保护编辑能力与调用条件。
  - 工作区静态契约测试：确保定时日报禁用、删除禁令不变。

## 验证

- MCP Node 测试全部通过。
- Skill 静态契约测试全部通过。
- 不在测试中访问真实禅道或上传真实文件。
- 实际更新 `BUG-3397` 前重新取得用户对具体步骤正文与图片的操作确认。
