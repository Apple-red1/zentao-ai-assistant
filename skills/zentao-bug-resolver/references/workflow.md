# zentao-bug-resolver workflow

本文件是 `SKILL.md` 的详细执行合同。它只描述当前实现支持的读取入口和已有基础 CLI；没有真实字段、模块名称查询或强并发令牌证据时，必须保留 unavailable/blocked，而不是补猜测。

仅要求 Bug URL 时，不进入本 workflow 的证据流程，直接使用固定路由的 `zentao.py bug web-url`；不调用浏览器或页面请求。

先选择路径：当前消息明确确认已解决，执行第 0 节；普通分析/修复请求执行第 1～7 节。**第 1～7 节的业务证据、账号、验证、compare 和 pending 隔离门槛只约束普通流程**，不得套用到第 0 节。

## 0. HUMAN_ATTESTED_RESOLVE

### 0.1 触发与当前授权（H-001）

当前消息必须明确表达“已解决 / 解决了 / 标记已解决”，并且每个目标可唯一确定。显式 Bug ID 优先；没有 ID 时仅能使用当前上下文唯一正在处理的 Bug。无目标或多个候选时提问，不能搜索后猜一个、从历史授权或 pending queue 补入 ID。人工确认同时构成当前 Bug 的 `RESOLVE_R2_ALLOWED`，不是 SOLVABLE 代码审计结论。

| 当前表达 | 路由 / 条件 |
|---|---|
| 3641 已解决 | HUMAN_ATTESTED_RESOLVE |
| Bug #3641 解决了，更新禅道 | HUMAN_ATTESTED_RESOLVE |
| 把刚才那个 Bug 标记已解决 | 上下文唯一才进入人工确认，否则提问 |
| 刚才那个已解决 | 无目标或多个目标时提问 |
| #3641、#3642 已解决 | 当前消息明确列出的 ID 按输入顺序串行处理 |
| 处理一下 | 普通流程，不授权 R2 |
| 看一下 | 普通流程，只读分析 |
| 修一下 | 普通流程，本地修复 |
| 帮我解决 Bug #3641 | 普通流程，不视为已解决 |
| 修复后标记已解决 | 普通流程，只有修复和证据门槛通过后才允许 R2 |
| 应该好了 | 不触发人工确认 |
| 可能没问题了 | 不触发人工确认 |

否定、假设、条件句或引用别人的话不等于当前用户的完成确认；必须理解整条消息，不能仅匹配“已解决”字样。此分支的目标列表只存在于本次请求，不成为持久队列，不继承普通流程的 pending 项。

### 0.2 跳过业务代码审计（H-007）

人工确认是本分支的最终业务结论，不重新证明。对目标业务 Bug **不执行也不要求**：业务仓库 `AGENTS.md`、`git status`、`git diff`、源码搜索/根因分析、附件/截图、commit/push/merge/SHA、test/lint/typecheck/build、业务修复 patch，也不运行 resolver 的 select/snapshot/compare。先前的代码门槛、验证失败或 snapshot 缺字段不应重新成为该分支门槛。

这里只跳过被处理业务 Bug 的审计；开发本 Skill 自身仍遵守本仓库的测试和 patch 交付规则。

### 0.3 单 Bug 的 CLI 顺序（H-002 / H-003 / H-005 / H-008）

1. 只执行一次最小 pre-view，判断对象存在、可访问及当前 status。不下载附件、不查询创建人或测试账号。

```bash
python skills/zentao/scripts/zentao.py bug view <id> --json
```

成功 JSON 可为 Bug 对象或 `{"bug": {...}}`；读取 Bug 对象内的 `status`，不能把响应外层 `status=success` 当作 Bug 状态。若有返回 ID 必须与目标一致。缺少/无法识别 status、非对象响应、ID 不一致、不可访问或不存在都停止并说明真实阻塞，不补猜测。

| pre-view 状态 | 下一步 |
|---|---|
| `active` | eligible；每个 active Bug 最多一次 resolve |
| `resolved` / `closed` | 不重复写，报告当前状态，可继续下一个明确 ID |
| 其它 / 不可识别 | 停止整个队列，说明状态并提问 |

2. 仅 active 时，按 comment-templates 的 Human-attested 模板生成 UTF-8 文件。用户有说明则保留原意，无说明不追问。默认文件放在项目 Git ignored 的 `.tmp/zentao/bug-resolver/`，逐 Bug 使用独立文件，不含认证秘密。

```bash
python skills/zentao/scripts/zentao.py bug resolve <id> \
  --resolution fixed \
  --resolved-build trunk \
  --comment-file <generated-human-attested-comment.txt> \
  --json
```

默认显式 `resolvedBuild=trunk`（主干）。用户明确指定其它解决版本时，将唯一的 `--resolved-build` 值覆盖为用户明确值，不追加第二个参数。基础 CLI 接受正整数版本 ID 或 `trunk`；无法表达的用户值按真实 CLI 校验错误反馈，不猜版本或把版本名当 ID。默认不传 `--assignee` 和 `--resolved-date`，不主动查询或追问负责人、备注、日期、版本、commit/push/merge。备注只记录人工确认及本次使用的版本参数，不伪造已验证的解决版本证据。

3. resolve 后必须通过另一个明确命令显式 post-view；基础 CLI 自身不自动 GET。

```bash
python skills/zentao/scripts/zentao.py bug view <id> --json
```

回读真实为 `resolved` 才报告“回读已解决”；如果 pre-view 原本就是 resolved/closed，应说明“原已处于该状态，本次未写入”。写响应成功不能替代回读。若写后读到 active/closed/其它状态、读失败或响应不合法，报告 API 与回读差异并停止，不能声称本次 resolve 已成功，不发送后续写入。写前 view 不是 CAS、ETag 或锁，不保证读写之间没有并发变化。

### 0.4 多 Bug、真实阻塞与未知结果（H-004 / H-006）

当前消息明确列出多个已解决 Bug 时按输入顺序去重，严格串行：前一项 pre-view → eligible resolve → post-view 完成后，才读取下一项。不并行发 lifecycle；已 resolved/closed 零写入后可继续。普通流程仍一次一个 current Bug，不因本分支放宽 pending 授权。

只有真实阻塞才反问：目标缺失/歧义、对象不存在/不可访问、状态不允许、权限拒绝、ZenTao 要求额外必填字段或其它必须由人决定的业务校验、未知写入后仍不能确认。错误命令 exit 非 0 时读取 stderr 的 `error.code/message/details`，按真实错误说明，不展示秘密。不得提前问元数据或审计事实。

- 校验/权限等明确失败（包括实际拒绝 trunk）：停在当前对象，不读取后续 Bug，携带真实错误提问；不猜版本、不自动重试，不自动填默认值后再写。必要的 post-view 只用于陈述当前状态，不能把失败改报为成功。
- `UNKNOWN_WRITE_RESULT`：立刻停止整个队列，绝不重试原 resolve，只读回读。即使回读为 resolved，也只报告“写入响应未知；当前回读为 resolved”，不自动继续剩余 ID；无法确认则保持 unknown 并请求人工决定。
- 401 只继承基础 CLI 认证层的一次刷新/重放，Agent 不再执行第二个 resolve 命令。
- 不通过 edit/close/activate、私有接口、数据库或 facade 绕过失败；不自动 close、activate、delete。

结束报告逐项给出实际状态、是否发送 resolve、实际回读和未处理 ID；不要求普通流程的分类、测试、diff 或 compare 报告。阻塞后的剩余对象等待用户新的明确指令。

## 1. 执行面

```text
确定性读取脚本
  select / snapshot / compare
    -> zentao programmatic public facade（只读）

Agent 普通证据工作流
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

在普通证据流程的任何 lifecycle 写入前重新运行：

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
