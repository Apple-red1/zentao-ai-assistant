# zentao-bug-resolver workflow

本文件是 `SKILL.md` 的详细执行合同。它只描述当前实现支持的读取入口和已有基础 CLI；没有真实字段、模块名称查询或强并发令牌证据时，必须保留 unavailable/blocked，而不是补猜测。

## 1. 执行面

```text
确定性读取脚本
  select / snapshot / compare
    -> zentao programmatic public facade（只读）

Agent 工作流
  读取上述 JSON + 业务仓库
    -> 最小代码修改/真实验证
    -> 写前 compare
    -> 基础 zentao CLI 的一次 Bug lifecycle resolve
    -> 显式 snapshot/view 回读
```

脚本不修改业务仓库，不执行任意 shell，不执行 ZenTao lifecycle。写入只能由 Agent 在本合同和当前用户授权同时满足时显式调用基础 CLI；这不改变 programmatic facade 的只读边界。

## 2. 当前 Bug 与队列

1. 运行 `select`；若使用多个 Bug ID，输入顺序去重，第一项为 `current_bug_id`，其余仅放入 `pending_queue`。
2. 只对 `current_bug_id` 读取详情、资源、代码、验证和 lifecycle；不要预读或处理 pending 项。
3. 当前 Bug 得出最终结论后停止本次任务。要处理下一项，用户必须再次明确继续，并重新解析该 Bug 的授权与起始 snapshot；当前 Bug 的授权不继承。
4. `complete=false`、`partial_failures` 或 `unsupported_filters` 必须在证据结论中明确。候选结果不完整时不能声称“没有其它 Bug”。

## 3. 授权等级

授权针对当前请求和当前 Bug，不从历史对话、其它 Bug 或 pending queue 继承。

| 用户表达 | 最高等级 | 允许范围 |
|---|---|---|
| 看看、分析、排查 Bug | `ANALYZE_ONLY` | ZenTao/代码读取、证据报告 |
| 修一下、修复、改代码解决 | `LOCAL_FIX_ALLOWED` | 上述范围 + 业务代码最小修改和验证；不写 ZenTao |
| 明确“更新禅道为已解决”“修复后 resolve 禅道 Bug” | `RESOLVE_R2_ALLOWED` | 上述范围 + 通过全部门槛后一次 eligible resolve |
| 模糊“处理这个 Bug” | `LOCAL_FIX_ALLOWED` | 不能推断 R2 |

不确定时只能降级。R2 只允许当前 Bug 的一个 `bug resolve`；不自动 close、activate、delete，也不以 edit/activate/close 仅留下分析 comment 或单独转派 active Bug。

## 4. 证据分类

### `SOLVABLE`

必须同时具备：

- 明确 Bug 对象和症状；
- 可复现条件，或足够确定的失败触发条件；
- 从当前证据可说明 actual behavior；
- 从 Bug/产品契约或其它当前证据可说明 expected behavior；
- 当前业务源码中的具体文件、symbol 或调用路径，直接证明不一致的根因；
- 可以命名最小修改边界；
- 没有工作区、资源、权限、测试或并发阻塞。

只有 `SOLVABLE` 且授权至少为 `LOCAL_FIX_ALLOWED` 时才可修改业务代码。

### `UNCLEAR`

复现、actual、expected 或其它必要事实缺失到修改意图不确定。不得修改代码。没有满足 D-003 的 R2 门槛时只输出缺失事实清单。

### `NO_CODE_EVIDENCE`

报告可能真实，但当前业务源码没有直接根因、负责 symbol 或可证明的修改点。不得凭业务常识猜测或修改代码；只有 D-003 的完整门槛才可走信息退回分支。

### `BLOCKED`

证据可能充分，但存在不安全或不可用条件，例如无关 dirty 工作区、关键资源失败、必要验证不可运行、权限拒绝、写前 snapshot 冲突、缺少显式 R2/测试账号或写结果未知。不得用替代 endpoint、私有接口或其它生命周期动作绕过。

## 5. 固定步骤

### 5.1 选择与起始快照

对 current Bug 运行：

```bash
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py snapshot --bug-id <id> --json
```

保存命令返回的完整 JSON 作为本次起始 baseline。原始 `bug` 用于证据审阅；`critical` 和 `unavailable_fields` 用于确定性复查。字段缺失保持 unavailable。创建人只有明确 account 证据才可形成 `creator_account`；只有姓名不能当账号。

需要附件或富文本资源时，显式运行已有只读入口：

```bash
python skills/zentao/scripts/zentao.py resource fetch --object-type bug --object-id <id> --json
```

资源失败若影响必需证据则 `BLOCKED`；非关键失败必须保留在报告中。

### 5.2 业务仓库门

在任何业务代码修改前：

1. 定位目标业务仓库根目录；
2. 读取该根目录的 `AGENTS.md`（若存在）；
3. 执行 `git status --short`；
4. 将无关或无法归属的 dirty 变更视为阻塞；不得 stash、reset、checkout、discard 或覆盖用户变更；
5. 只使用该仓库文件和约束中真实存在的测试、lint、typecheck、build 命令；不存在的命令不能为了“满足验证”而编造。

### 5.3 源码、修改与验证门

`SOLVABLE + LOCAL_FIX_ALLOWED` 以上才进入修改门。记录具体文件/symbol/call path，做能解释根因的最小变更。随后运行与变更面对应且仓库确实定义的验证命令；成功前不能称为 fixed。检查 `git diff`：只包含当前 Bug 所需的最小变更，没有用户无关变更或秘密。

### 5.4 写前并发复查

在任何 lifecycle 写入前重新运行：

```bash
python skills/zentao-bug-resolver/scripts/zentao_bug_resolver.py compare --bug-id <id> --baseline-file <start-snapshot.json> --json
```

`changed=true` 是硬阻塞，停止所有写入，不覆盖人工变化。若输出 `comparison_blocked=true`、`block_reason=CRITICAL_FIELD_UNAVAILABLE` 或 `unavailable_fields` 非空，也必须按关键事实不可安全比较处理，停止写入；只有完整且明确为 `changed=false` 的结果才可继续评估其它 R2 门槛。该检查是“写前只读并发复查”，不是 CAS、ETag、锁或强一致保证。

### 5.5 fixed R2 分支

必须同时满足：

- 当前用户对当前 Bug 明确给出 `RESOLVE_R2_ALLOWED`；
- 分类为 `SOLVABLE`；
- 直接代码证据和最小修改已完成；
- 实际验证通过，diff 已审阅；
- compare 未变化；
- 明确、可用的测试账号和 endpoint 所需 resolved-build 事实存在（没有依据时不得填默认值）。

把实际观察/修改/测试结果填入 fixed comment 模板后，只调用一次：

```bash
python skills/zentao/scripts/zentao.py bug resolve <id> \
  --resolution fixed \
  [--resolved-build <fact-supported-build-or-trunk>] \
  --assignee <explicit-test-account> \
  --comment-file <utf8-file> \
  --json
```

完成后显式 snapshot 或 `bug view` 回读并报告状态；不自动 close。

### 5.6 unclear/no-code 信息退回分支

这不是技术修复结论。只在以下条件全部满足时允许一次写入：

- 当前用户明确给出当前 Bug 的 `RESOLVE_R2_ALLOWED`；
- 当前状态实际为 active；
- 起始/当前 snapshot 提供非空、明确 account 形式的 `creator_account`；
- 写前 compare unchanged；
- 使用 `[CODEX-BUG-UNCLEAR]` 模板，明确写“本次未修改业务代码”、证据不足和补充清单。

此时只调用一次：

```bash
python skills/zentao/scripts/zentao.py bug resolve <id> \
  --resolution will-not-fix \
  --assignee <snapshot.creator_account> \
  --comment-file <utf8-file> \
  --json
```

模板必须说明：这里的 `will-not-fix` 是信息不足退回流程，不是已修复或无问题结论；补齐信息后需要用户显式 `activate` 再进入处理。缺少任一门槛时不写入、不改代码，只报告 missing facts。

## 6. 错误与安全

- `UNKNOWN_WRITE_RESULT`：绝不重试原 resolve；只读 snapshot/view 确认，不能明确证明预期状态就保持 unknown/blocked，并停止其它写入。
- 401：只继承基础 CLI 认证层已经冻结的一次刷新/重放；workflow 不增加循环重试。
- 403 或其它权限拒绝：主分类仍为 `BLOCKED`，可在报告中使用原因码 `BLOCKED_PERMISSION`；不切换 edit/activate/close、私有接口或数据库。
- 比较冲突、关键资源失败、验证失败、无关 dirty workspace：`BLOCKED`，保留证据和 exact reason。
- 日志、comment 和最终报告不得包含密码、Token、认证 header、`.env` 内容、完整私密配置或不必要的内部地址。

## 7. 结束条件

一次当前 Bug 处理必须报告：分类、授权等级、证据范围、验证命令与实际结果、diff 范围、compare 结果、lifecycle/readback 结果、未验证限制和 pending 数量。没有显式继续授权时在此停止。
