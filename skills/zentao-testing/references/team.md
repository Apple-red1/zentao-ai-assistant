# 测试团队配置合同

测试团队归 `zentao-testing`，与 `zentao-personal` 的开发/个人默认团队是两个独立配置域。
两类团队可以同时存在、分别查询和分别更新；测试团队操作不得写入
`~/.zentao-ai-assistant/teams/`。

## 模型与入口

第一版只提供一个全局默认测试团队，以及每个已保存测试项目最多一个完整覆盖团队：

```text
global default testing team
  + project-specific complete override (optional)
```

配置入口从测试 Skill 执行：

```bash
python3 skills/zentao-testing/scripts/zentao_testing.py team-view --json
python3 skills/zentao-testing/scripts/zentao_testing.py team-add --member alice --json
python3 skills/zentao-testing/scripts/zentao_testing.py team-remove --member alice --json
python3 skills/zentao-testing/scripts/zentao_testing.py team-replace --member alice --member bob --json
python3 skills/zentao-testing/scripts/zentao_testing.py team-replace --clear --json
python3 skills/zentao-testing/scripts/zentao_testing.py project-team-replace \
  --project-alias mall --member alice --member bob --json
python3 skills/zentao-testing/scripts/zentao_testing.py project-team-reset \
  --project-alias mall --json
python3 skills/zentao-testing/scripts/zentao_testing.py team-import-personal --json
```

这里的 `team-*` 只表示测试团队；个人/开发团队仍使用
`skills/zentao-personal/scripts/zentao_personal.py team-*`。用户只说“设置团队”且无法判断
类型时，先澄清“开发/个人团队，还是测试团队”，写入次数为 0。

## 解析与覆盖

- 成员输入可以是完整用户目录中的精确 account 或唯一姓名；姓名不写入配置。
- 当前登录 account 运行时自动加入，不重复保存。
- 测试项目覆盖完整替代全局默认团队，不隐式合并；没有覆盖时回退全局默认团队。
- 项目覆盖只允许针对 `testing-projects` 中已保存的项目别名；全局和其它项目保持不变。
- `team-import-personal` 只有用户明确要求时执行一次性复制；导入后两份名单不自动同步。
- 返回值包含 `source`、`project_alias`、`configured_accounts`、`effective_accounts`、
  `complete` 和 `partial_failures`，明确区分 `global_default`、`project_override` 和
  `explicit_personal_import`；同时返回 `team_domain=testing`，与个人团队的
  `team_domain=personal_development` 区分。

## 持久化与失败语义

测试团队固定写入：

```text
~/.zentao-ai-assistant/testing-teams/<identity-sha256>.json
```

它与个人团队的 `teams/` 和测试项目上下文的 `testing-projects/` 分离，均按规范化
base URL + 当前 account 隔离。成员写入前完整读取 inside/outside 用户目录；分页不完整、
账号冲突、姓名重名、账号不存在、配置损坏、schema/owner 不匹配、符号链接、并发锁或
原子写失败均不覆盖旧配置，也不影响另一配置域。

配置不保存密码、Token 或姓名；目录/文件权限目标为 `0700/0600`，使用独占锁、临时文件
flush/fsync 和原子替换。独立查询只代表当前读取结果，不构成跨文件事务或强一致 CAS。
