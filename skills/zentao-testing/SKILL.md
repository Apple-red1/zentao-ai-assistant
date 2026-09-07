---
name: zentao-testing
description: "测试端 ZenTao Bug 工作台：独立保存测试团队与项目覆盖、持久化测试项目和模块负责人，整理并创建 Bug，查询本人未关闭 Bug，以及查看、备注、激活、关闭和在已验证环境中独立指派 Bug。"
---

# zentao-testing

本 Skill 面向测试工作流；开发端的 Bug 根因调查、代码修复和解决流程继续由
`zentao-bug-resolver` 负责。测试项目只是当前工作上下文，不是开发/测试权限边界。

## 入口和确定性脚本

项目与模块配置由脚本保存到用户级、按 ZenTao 实例和当前账号隔离的配置文件：

```text
~/.zentao-ai-assistant/testing-projects/<identity-sha256>.json
```

可用入口：

```text
python3 skills/zentao-testing/scripts/zentao_testing.py project-set
python3 skills/zentao-testing/scripts/zentao_testing.py project-list
python3 skills/zentao-testing/scripts/zentao_testing.py module-set
python3 skills/zentao-testing/scripts/zentao_testing.py context-use
python3 skills/zentao-testing/scripts/zentao_testing.py context-view
python3 skills/zentao-testing/scripts/zentao_testing.py project-remove
python3 skills/zentao-testing/scripts/zentao_testing.py module-remove
python3 skills/zentao-testing/scripts/zentao_testing.py my-bugs
python3 skills/zentao-testing/scripts/zentao_testing.py my-bugs --all-projects
python3 skills/zentao-testing/scripts/zentao_testing.py team-view --json
python3 skills/zentao-testing/scripts/zentao_testing.py team-replace --member alice --member bob --json
python3 skills/zentao-testing/scripts/zentao_testing.py project-team-replace --project-alias mall --member alice --json
python3 skills/zentao-testing/scripts/zentao_testing.py team-import-personal --json
```

脚本负责 ID、分页、去重、配置安全和结果完整性；它不直接写 ZenTao，也不读取
内部 HTTP 实现。所有 ZenTao 写入都必须回到基础 `zentao` CLI。
聊天中展示 Bug 编号时遵守统一的 [Bug 展示说明](../zentao/references/bug-display.md)，
使用基础公开 URL 合同，不猜测或拼接实例地址。

## 配置合同

- 一个测试项目绑定一个 Product 和一个默认 `affected-build`；真实 Project ID 可选。
- 没有 Project ID 时不强求 Project/Product 关联，`my-bugs` 默认按 Product 查询。
- 一个模块保存一个真实 Module ID、一名前端 account 和一个后端 account。
- Product/Build/用户候选必须完整且唯一；提供 Project ID 时 Project/Product 候选和关联也必须完整，无法证明关联时结果要标记不完整，不能假装已验证。
- 姓名只用于输入，保存前必须从完整用户目录唯一解析为真实 account。
- Project/Product 或默认 build 更新会把已有模块标记为 stale；重新 `module-set` 后才可作为完整当前上下文。
- `context-use` 只切换已保存的项目和模块，不自动挑选第一个项目。

## 测试团队与开发/个人团队

测试团队是独立配置域，保存于 `~/.zentao-ai-assistant/testing-teams/<identity-sha256>.json`；
`zentao-personal` 的开发/个人团队继续保存于 `teams/`，两者可以共存、分别查询和分别更新。
本 Skill 的 `team-view/add/remove/replace` 只操作测试团队全局默认名单；
`project-team-view/add/remove/replace/reset` 只操作指定已保存测试项目的完整覆盖名单。
项目覆盖存在时替代全局默认测试团队，不隐式合并；不存在时回退全局默认测试团队。
当前登录账号只在运行时自动加入，不保存为成员。

`team-import-personal` 仅在用户明确要求“一次性导入个人/开发团队为测试团队”时执行，
导入后不自动同步。设置、查询和更新结果都说明 `source`、项目范围和是否影响其它团队。
用户只说“设置团队”而无法判断类型时，必须先询问“要设置开发/个人团队，还是测试团队？”，
在类型明确前不得写入；明确说“测试团队”时不得提示覆盖开发/个人团队。

成员写入前完整解析真实用户目录；目录不完整、账号冲突、姓名重名或账号不存在时不写入。
损坏、并发或原子写失败只影响目标配置域，不覆盖另一域。详细 schema、路径和失败语义见
[测试团队配置合同](references/team.md)。

## 提 Bug 和分派

用户明确说“提 Bug”或“创建 Bug”即授权一次 R1 创建，不展示草稿等待第二次确认。
先读取 `context-view`，确认 Product/Module/default build 和两个负责人均可用；Project ID
如已配置则一并使用，再
整理用户已提供的标题、前置条件、复现步骤、实际结果、期望结果和证据。不得补造浏览器、
状态码、测试数据或业务规则；步骤图片按基础 `bug create --steps-inline-image` 合同传入，
不能改走备注。

分派优先级固定为：

```text
explicit_assignee > explicit_frontend/backend > evidence_frontend/backend > default_backend
```

每次结果必须展示 `assigned_to` 和 `assignment_source`。`default_backend` 只表示按项目规则
交给后端负责人，不表示 AI 已证明根因属于后端。可用纯函数入口检查该规则：

```text
python3 skills/zentao-testing/scripts/zentao_testing.py assignment \
  --frontend-account frontend --backend-account backend
```

确认上下文后，创建动作只调用一次基础命令，例如 `zentao.py bug create`；成功后使用基础
`bug web-url` 返回可点击 Bug 编号。多行步骤按基础 Skill 的统一文本合同整理为真实 LF，
优先使用受控 UTF-8 临时文件传给 `bug create --steps-file`；若输入是序列化字符串才使用
`--steps-json`，只解码一次，不复制另一套 `\\n` 替换逻辑。写入失败或结果未知不重试、不补备注。

## 我的 Bug

`my-bugs` 默认读取当前测试项目 Product 范围的全部 Bug；配置了 Project ID 时使用 Project
范围，没有 Project ID 时使用 Product 范围（均不默认限制当前模块）；只有显式
`--all-projects` 才扫描所有可见 Product/Project/Execution 范围。结果只保留当前账号负责、
状态不是 `closed` 的 Bug，完整分页、去重、稳定排序，并保留 `complete` 和
`partial_failures`。不完整的空结果不能解释为“没有 Bug”。Bug ID 的链接来自基础 Skill
公开 URL 合同。

## 日常操作和边界

测试语境可以路由：查看、备注、明确激活、明确关闭和独立指派。查看使用基础
`bug view`；备注使用基础 `bug comment`；激活/关闭保持各自的 R2 意图和回读；备注图片
只在用户明确说是备注时使用 comment 的附件合同。

active Bug 独立指派只有在专用 ZenTao 21.7.8 环境完成能力探测并证明写后字段保真后，才可
使用基础层的 compatibility 能力。若环境没有通过该门槛，应报告
`INCONCLUSIVE/ENVIRONMENT_BLOCKER`，绝不用生命周期动作代替指派；不接受任意 URL、Cookie、
数据库或第二套 transport。

测试端不接管“修 Bug、查根因、标记已解决”等开发语义，也不把回归通过映射为解决动作。
所有输出必须区分真实成功、未执行、部分失败、未知写结果和未验证能力。
