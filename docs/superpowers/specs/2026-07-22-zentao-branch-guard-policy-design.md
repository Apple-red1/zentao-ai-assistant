# 禅道代码写入分支门禁调整设计

## 目标

调整个人 Bug 代码辅助流程的分支门禁：不再要求当前分支精确等于仓库配置中的 `targetBranch`，改为基于分支名称的禁用规则，同时保留其余仓库安全检查。

## 分支规则

分支比较不区分大小写。

- 当前分支以 `dev`、`test` 或 `release` 开头时拒绝代码写入。
- 当前分支精确等于 `main` 或 `master` 时拒绝代码写入。
- 其他分支不因名称被拒绝，例如 `0720-temp`、`wwt_play`、`feature/main-fix`。
- `targetBranch` 不参与当前分支是否允许写入的判断。为保持现有配置兼容性，本次不删除配置字段。

因此，`dev`、`development-x`、`test`、`test_fix`、`release` 和 `release/1.0` 均被禁止；`feature/main-fix` 不会因为包含 `main` 而被禁止。

## 保留的安全门禁

本次只调整分支名称策略。以下门禁保持不变：

- `codeWriteEnabled` 必须为 `true`。
- Bug 必须唯一映射到一个配置仓库。
- 必须是普通主 checkout，且 HEAD 不得分离。
- 工作树和暂存区必须干净。
- 当前分支必须存在上游。
- 本地与上游必须满足 `ahead/behind=0/0`。
- 必须取得任务、Bug 和仓库租约。
- 结构化历史、稳定快照、测试白名单及并发复核仍须通过。

## 修改范围

- 修改仓库 guard 的分支判定实现。
- 更新 `zentao-ai-bug` 的 `SKILL.md`、`personal-bug-agent.md` 和相关分析说明，删除“必须等于 `targetBranch`”的描述并写明新规则。
- 保留配置 schema 中的 `targetBranch`，避免破坏已有配置；该字段继续作为兼容元数据，但不授权或限制代码写入。
- 更新回归测试和兼容性契约。

## 测试设计

- 拒绝 `dev`、`development-x`、`test_fix`、`release/1.0`，并验证大小写不敏感。
- 拒绝精确的 `main`、`master`。
- 允许 `0720-temp`、`wwt_play`、`feature/main-fix`。
- 当前分支与 `targetBranch` 不同但满足其他条件时，不因分支名称被拒绝。
- 现有工作区、上游和同步状态门禁仍然有效。

## 发布

在当前 `feature/zentao-open-source` 分支追加设计和实现提交，运行完整验证后推送到 `origin/feature/zentao-open-source`。随后从该远程分支重新安装本地 CLI/插件，并用实际门禁命令复测规则。
