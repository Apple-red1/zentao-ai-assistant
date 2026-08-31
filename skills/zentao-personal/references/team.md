# 个人默认团队：名单、Bug 与日报

本功能归 `zentao-personal`，不新增 Skill/API endpoint。初始需求依据为
[Issue #48 的决策评论](https://github.com/Apple-red1/zentao-ai-assistant/issues/48)，
阶段归属由 [Issue #58](https://github.com/Apple-red1/zentao-ai-assistant/issues/58)
修订为 `active → assignedTo`、`resolved → resolvedBy`。

## 自然语言与命令

命令从仓库根目录执行，Plugin 中替换为插件副本内脚本的实际路径。

| 用户意图 | `zentao_personal.py` 参数 |
|---|---|
| 查看我的团队 | `team-view --json` |
| 添加成员 | `team-add --member alice --member 张三 --json` |
| 移除成员 | `team-remove --member alice --json` |
| 把我的团队整体替换为这些成员 | `team-replace --member alice --member bob --json` |
| 清空配置的成员 | `team-replace --clear --json` |
| 查询团队的 Bug | `team-bugs --markdown` |
| 查询今日团队日报 | `team-brief --markdown` |

只有用户明确要求添加、移除、替换或清空时执行对应名单写入；“添加”不能解释为
整体替换，含糊的名单调整先澄清。查看和查询不创建/覆盖团队文件。
替换空列表必须显式 `--clear`；遗漏成员参数是用法错误，不会清空名单。
本人不写入配置成员，移除本人或清空成员也不会将本人移出有效查询范围。

成员输入复用共享唯一用户解析：精确 account → 精确姓名 → 唯一的忽略大小写
account。写入前完整读取 `inside/outside` 所有页；重名、账号不存在、目录冲突、
任何分页/权限失败都停止且不修改名单。最终只保存真实 account，不保存姓名。
查询时缺失成员仍显示账号与不完整状态，不猜替代用户，保留其他成员已取得结果。

## 查询范围与事实

- 默认本人 + 当前站点/账号配置的唯一团队，查询当前认证账号所有可见范围。
- 全范围完整扫描 Product、Project、Execution 列表及其 Bug 列表，统一 `browse=all`；
  不使用会漏掉 resolved 的 `unresolved`。跨范围按 Bug ID 去重。
- 可选 `--product <id>`、`--project <id>`、`--execution <id>` 互斥，只缩小本次查询；
  不修改团队名单，不支持 `--user` 切换别人的团队。
- `active` 使用当前 `assignedTo` 的 account（兼容 `assignedTo.account` /
  `assignedToAccount`）归入“需要马上行动”；团队外负责人、空值和特殊值 `closed`
  不分配给团队成员，历史 `resolvedBy` 不参与当前归属。
- `resolved` 使用 `resolvedBy` 的 account（兼容 `resolvedBy.account` /
  `resolvedByAccount`）归入解决人的“待测试验证”；当前 `assignedTo` 只表示测试负责人，
  无论其是否属于团队都不改变归属。同一 Bug 只归解决人一次；`closed` 不纳入。
- `resolvedBy` 缺失、非法或矛盾时报告 `BUG_RESOLVER_INVALID`，不回退到当前负责人；
  团队内解决人的 `assignedTo` 无效时仍保留 Bug，以 `—` 展示测试负责人并报告
  `BUG_VERIFICATION_ASSIGNEE_INVALID`。未知/缺失状态、无效 ID、无法解析阶段负责人或
  同 ID 快照冲突也进入失败信息，不静默归类。
- 不提供事务快照；分页/跨范围读取期间如果同 ID 的关键事实冲突，排除冲突项并报告
  `BUG_SNAPSHOT_CONFLICT`。不能把多次独立查询间的真实变化误认为两种入口数据不一致。

## 共享排序与展示

1. 先 active，后 resolved；每个阶段内本人在前，其余成员按 account 升序。
2. 同成员内按优先级 1–4、严重程度 1–4、`openedDate` 升序、数值 Bug ID 升序。
   优先级或严重程度缺失/非法的项排在该成员阶段末尾，原始字段不改写。
3. 同优先级/严重程度下，创建时间缺失或非法排末尾并报告 `BUG_DATE_INVALID`；
   可比较的带时区时间换算 UTC，同组混合带/不带时区时报告
   `BUG_DATE_INCOMPARABLE` 并改用 ID 稳定排序，不猜本地时区。
4. “需要马上行动”固定四列：`Bug ID / 标题 / 优先级 / 状态`；“待测试验证”固定
   五列：`Bug ID / 标题 / 优先级 / 状态 / 当前测试负责人`。标题保留真实内容并
   转义 Markdown，优先级或测试负责人缺失显示 `—`，状态显示“激活/已解决”。
5. 两个阶段都保留全部成员；只有完整且无结果才显示 `0` 和“暂无符合条件的 Bug”。
   不完整成员显示“数据不完整”，已有数量只能称作“已获取”。
6. 日报只在相同明细前添加快照日期和团队汇总，不删减普通 Bug，不重新排序或查询重点项。
   用户同时要两种展示时复用本次已获取结果，不为换一种展示再次请求同一批数据。

`--markdown` 调用基础 `bug web-url`，按返回的 `id → url` 关联编号链接；不拼 URL、
不访问页面。链接生成失败保留所有行并明确说明，不改变数据层 `complete`。
遵守[共享 Bug 展示规则](../../zentao/references/bug-display.md)。
默认终端输出格式化 JSON；`--json` 输出紧凑机器 JSON，保留原始字段与 ID，无 Markdown。

## JSON 与完整性

两种查询使用同一结果模型：`scope`、`snapshot_date`、`effective_accounts`、
`bug_ids`、`summary`、`active`、`awaiting_verification`、`duplicates_removed`、
`complete`、`partial_failures`。同一输入快照产生相同 JSON，不因入口改变过滤。

`active/awaiting_verification` 每项为
`{account, realname, bugs, complete, partial_failures}`；所有数字由脚本计算。
`summary.total_not_closed = active_immediate_action + resolved_awaiting_verification`。
`bug_ids` 是数值升序的规范化 ID 集合，明细保留 API 原始 ID；数量只计算已获取的有效项。
`awaiting_verification` 的成员 account 是规范化 `resolvedBy`，Bug 原始 `assignedTo`
保留给机器数据和“当前测试负责人”展示，不形成第二份统计归属。

`--per-page 1..1000` 默认 1000；读取途中失败保留已读页，其他范围继续。
整个 scope 的失败会影响全部成员完整性；单成员数据异常保留在对应成员和总结果中。
返回部分事实时 exit 0，但 `complete=false`；阻塞配置、解析/运行错误 exit 1，
错误 JSON 在 stderr；用法错误 exit 2。不能只看退出码声称数据完整。
`--today YYYY-MM-DD` 只用于指定快照日期（例如测试），不筛选 Bug；正常查询省略。
`--cache-data` 将当前报告存入既有 scope 的 `personal` 临时目录，不能用作名单事实源。

## 持久化与安全

详见[配置文档](../../../docs/configuration.md#个人默认团队)。固定路径：
`~/.zentao-ai-assistant/teams/<identity-sha256>.json`，不接受任意输出路径。
连接仍遵守 project/user 配置选择；团队名单在两种模式中始终使用用户级持久化。
按规范化站点 URL + 当前 account 隔离，不把密码或 Token 写入团队文件。
目录/文件权限为 0700/0600，原子替换，拒绝损坏配置、未知版本、归属冲突和符号链接。
写入使用每身份独占锁目录，竞争返回 `TEAM_CONFIG_BUSY`；进程异常退出遗留的锁
需人工确认进程已结束后处理，不自动抢锁。该锁仅保护本地名单，不锁定 ZenTao 数据。

只提供本机一个默认团队，不提供多个命名团队、云同步、组织架构管理或生命周期写入。
Bug 数量不能解释为个人绩效。
