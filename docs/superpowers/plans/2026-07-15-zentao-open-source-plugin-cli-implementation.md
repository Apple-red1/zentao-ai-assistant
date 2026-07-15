# 禅道 AI 助手开源插件与 CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不删减现有禅道助手功能和安全门槛的前提下，将当前本地项目改造成同时交付 Python CLI、Codex 插件和内置 MCP Server 的开源单仓库项目。

**Architecture:** CLI、Codex 插件、定时任务和 MCP Server 只作为入口，共同调用 `src/zentao_ai` 中的配置、安全、工作流、持久状态、报告和禅道 Provider。迁移采用兼容外壳：先冻结当前行为，再移动实现，旧脚本入口保留一个版本周期并调用新核心。

**Tech Stack:** Python 3.11+、Typer、Pydantic 2、PyYAML、keyring、httpx、SQLite、MCP Python SDK、pytest、Ruff、mypy、Hatchling、GitHub Actions、Codex Plugin。

## Global Constraints

- Windows、macOS、Linux 均受支持；Windows 必须完成真实测试禅道验收。
- 当前所有功能、安全门槛、幂等合同、MCP 字段及 `templateVersion=v2` 报告合同必须保留。
- 删除 Bug 永久禁止，不存在配置开关、人工确认或管理员豁免。
- 受保护动作必须绑定当前轮次的具体 Bug、动作和完整参数；定时任务不得执行受保护动作。
- 图片仅接受当前轮次由用户明确提供的绝对本地路径，格式限 png、jpg、jpeg、webp，大小不超过 10 MiB。
- 密码、Token、Cookie、真实域名、团队成员、Bug 数据、报告、ledger、checkpoint、outbox 和绝对业务路径不得进入 Git。
- CLI、MCP 和 Codex Skill 不得各自复制业务规则；规则只能存在于共享核心。
- 每个任务按 TDD 执行：先失败测试、再最小实现、再回归测试、最后提交。
- 在任何 GitHub 推送前，`gh auth status` 必须成功，且秘密扫描必须通过。

---

## 文件结构锁定

```text
F:\每日工作\
├─ pyproject.toml
├─ README.md
├─ LICENSE
├─ SECURITY.md
├─ CONTRIBUTING.md
├─ CHANGELOG.md
├─ .gitignore
├─ src\zentao_ai\
│  ├─ __init__.py
│  ├─ cli\
│  ├─ config\
│  ├─ credentials\
│  ├─ zentao\
│  ├─ mcp_server\
│  ├─ workflows\
│  ├─ routing\
│  ├─ safety\
│  ├─ repository\
│  ├─ state\
│  ├─ reporting\
│  └─ scheduling\
├─ plugins\zentao-ai-bug\
│  ├─ .codex-plugin\plugin.json
│  ├─ skills\zentao-ai-bug\
│  ├─ scripts\
│  └─ .mcp.json
├─ config\
│  ├─ team.example.yaml
│  └─ personal.example.yaml
├─ scripts\
└─ tests\
   ├─ unit\
   ├─ contract\
   ├─ integration\
   └─ e2e\
```

---

### Task 1: 建立安全基线和有效 Git 仓库

**Files:**
- Create: `.gitignore`
- Create: `.gitattributes`
- Create: `tests/contract/test_repository_hygiene.py`
- Preserve locally: `.codex/zentao-ai-bug.yaml`
- Preserve locally: `reports/`

**Interfaces:**
- Consumes: 当前工作区及本地敏感配置。
- Produces: 可安全初始化的 Git 工作区；`assert_no_tracked_sensitive_paths(root: Path) -> None` 合同测试。

- [ ] **Step 1: 备份本地运行数据但不复制到仓库外的公共位置**

运行：

```powershell
Copy-Item -LiteralPath .codex\zentao-ai-bug.yaml -Destination .codex\zentao-ai-bug.yaml.local-backup
```

预期：本地备份存在；后续 `.gitignore` 同时忽略原文件和备份。

- [ ] **Step 2: 编写失败的仓库卫生测试**

测试必须拒绝以下路径被 Git 跟踪：`.codex/zentao-ai-bug.yaml`、`reports/`、`*.sqlite3`、`.env`、`*outbox*`、`*checkpoint*`、`*.local-backup`，并扫描文本中的 `password`、`cookie`、`token` 键是否带非环境变量值。

运行：

```powershell
python -m pytest tests/contract/test_repository_hygiene.py -v
```

预期：FAIL，因为 `.gitignore` 尚不存在。

- [ ] **Step 3: 添加忽略规则和文本规范**

`.gitignore` 至少包含：

```gitignore
.codex/zentao-ai-bug.yaml
.codex/*.local-backup
.env
.env.*
reports/
state/
ledger/
outbox/
*.sqlite3
*.cookie
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
```

`.gitattributes` 固定 `*.py text eol=lf`、`*.md text eol=lf`、`*.ps1 text eol=crlf`。

- [ ] **Step 4: 修复空 `.git` 并初始化仓库**

先确认 `F:\每日工作\.git` 内没有有效 Git 数据；将空目录改名为 `.git.invalid-backup`，然后运行：

```powershell
git init -b main
git status --short
```

预期：Git 正确识别仓库，敏感路径不出现在待跟踪列表中。

- [ ] **Step 5: 执行秘密扫描和测试**

```powershell
python -m pytest tests/contract/test_repository_hygiene.py -v
git status --short
```

预期：PASS；输出中没有 `.codex/zentao-ai-bug.yaml`、`reports/` 或数据库文件。

- [ ] **Step 6: 提交安全基线**

```powershell
git add .gitignore .gitattributes tests/contract/test_repository_hygiene.py docs/superpowers/specs/2026-07-15-zentao-open-source-plugin-cli-design.md docs/superpowers/plans/2026-07-15-zentao-open-source-plugin-cli-implementation.md
git commit -m "chore: establish safe open-source repository baseline"
```

---

### Task 2: 冻结现有行为并消除本机绝对路径测试依赖

**Files:**
- Create: `tests/legacy/`
- Create: `tests/contract/test_legacy_feature_inventory.py`
- Modify: `tests/test_config_contract.py`
- Modify: `tests/test_skill_contract.py`
- Modify: `tests/test_zentao_skill_contract.py`
- Modify: `tests/test_automation_contract.py`
- Modify: `tests/test_project_registration.py`
- Modify: `tests/test_register_codex_project.py`

**Interfaces:**
- Consumes: 当前项目脚本、用户级 Skill 和自动化合同。
- Produces: `LEGACY_FEATURES: frozenset[str]`，明确列出个人报告、团队报告、评论、步骤、图片、路由、修复、租约、幂等、定时任务和禁止删除等功能。

- [ ] **Step 1: 记录当前测试基线**

```powershell
python -m unittest discover -s tests -v
```

预期：保存每个 PASS/FAIL 结果；环境缺失导致的失败必须分类为路径耦合、外部 Skill 耦合或真实配置耦合，不得删除测试。

- [ ] **Step 2: 编写功能清单合同测试**

`test_legacy_feature_inventory.py` 必须逐项断言设计文档中的完整功能存在对应合同测试，并断言 `delete_bug`、`remove_bug` 只出现在拒绝合同中。

- [ ] **Step 3: 将绝对路径替换为仓库相对 fixture**

使用 `Path(__file__).resolve().parents[...]` 定位仓库；测试配置改用 `tests/fixtures/config/valid.yaml`；Skill 测试改用未来插件目录 `plugins/zentao-ai-bug/skills/zentao-ai-bug`；自动化测试改用 `tests/fixtures/automations`。

- [ ] **Step 4: 复制用户级 Skill 为迁移输入**

将以下文件复制到 `plugins/zentao-ai-bug/skills/zentao-ai-bug/`：`SKILL.md`、`personal-bug-agent.md`、`team-bug-report.md`、`bug-analysis.md`、`bug-summary.md`、`agents/openai.yaml`。复制后不得修改合同文字，先让测试针对仓库副本通过。

- [ ] **Step 5: 运行基线合同**

```powershell
python -m pytest tests/test_render_report.py tests/test_skill_contract.py tests/test_zentao_skill_contract.py tests/contract/test_legacy_feature_inventory.py -v
```

预期：全部 PASS。

- [ ] **Step 6: 提交行为基线**

```powershell
git add tests plugins/zentao-ai-bug/skills
git commit -m "test: freeze existing Zentao assistant behavior"
```

---

### Task 3: 创建可安装 Python 包和质量工具链

**Files:**
- Create: `pyproject.toml`
- Create: `src/zentao_ai/__init__.py`
- Create: `src/zentao_ai/py.typed`
- Create: `tests/unit/test_package_metadata.py`

**Interfaces:**
- Produces: `zentao_ai.__version__: str`；命令入口 `zentao-ai = zentao_ai.cli.app:main`。

- [ ] **Step 1: 编写包元数据失败测试**

断言包名为 `zentao-ai-assistant`、版本为 `0.1.0`、Python 下限为 3.11，并能导入 `zentao_ai.__version__`。

- [ ] **Step 2: 创建 `pyproject.toml`**

运行依赖固定为兼容范围：`typer>=0.12,<1`、`pydantic>=2.7,<3`、`PyYAML>=6,<7`、`keyring>=25,<26`、`httpx>=0.27,<1`、`mcp>=1,<2`。开发依赖包含 pytest、pytest-cov、ruff、mypy、build、twine。

- [ ] **Step 3: 安装开发环境并运行检查**

```powershell
python -m pip install -e ".[dev]"
python -m pytest tests/unit/test_package_metadata.py -v
python -m ruff check src tests
python -m mypy src
```

预期：全部 PASS。

- [ ] **Step 4: 验证构建**

```powershell
python -m build
python -m twine check dist\*
```

预期：生成 wheel 和 sdist，twine 检查通过。

- [ ] **Step 5: 提交包骨架**

```powershell
git add pyproject.toml src tests/unit/test_package_metadata.py
git commit -m "build: add installable Zentao assistant package"
```

---

### Task 4: 实现版本化配置、覆盖规则和脱敏

**Files:**
- Create: `src/zentao_ai/config/models.py`
- Create: `src/zentao_ai/config/loader.py`
- Create: `src/zentao_ai/config/redaction.py`
- Create: `src/zentao_ai/config/migrations.py`
- Create: `config/team.example.yaml`
- Create: `config/personal.example.yaml`
- Create: `tests/unit/config/`
- Create: `tests/fixtures/config/valid.yaml`

**Interfaces:**
- Produces: `load_config(project_path: Path, team_path: Path | None = None) -> AppConfig`；`validate_config(path: Path) -> ValidationResult`；`redact_config(config: Mapping[str, Any]) -> dict[str, Any]`。

- [ ] **Step 1: 编写配置合并和失败关闭测试**

覆盖内置默认值、团队配置、个人配置的优先级；缺少 `personal.scopeNames`、`team.scopeNames`、唯一仓库映射、目标分支、最大 Bug 数或权限字段时必须返回字段级错误。

- [ ] **Step 2: 定义 Pydantic 配置模型**

配置顶层包含 `configVersion: 1`、`zentao`、`personal`、`team`、`limits`、`repositories`、`permissions`、`reporting`、`schedule`。`permissions.codeWriteEnabled`、`commentEnabled` 和 `stepUpdateEnabled` 默认均为 `false`。

- [ ] **Step 3: 迁移现有校验规则**

从用户级 `run-ledger.py` 的 `validate_config_data` 提取规则，保持字段名和 `redactedConfig` 输出合同；旧 JSON 格式 YAML 继续可读。

- [ ] **Step 4: 添加脱敏示例配置**

示例只使用 `https://zentao.example.com`、`example-account`、`C:/code/example-project` 等虚构值，秘密字段使用 `${ZENTAO_TOKEN}` 形式。

- [ ] **Step 5: 运行配置测试**

```powershell
python -m pytest tests/unit/config tests/test_config_contract.py -v
```

预期：全部 PASS，测试输出不包含秘密值。

- [ ] **Step 6: 提交配置核心**

```powershell
git add src/zentao_ai/config config tests/unit/config tests/fixtures/config tests/test_config_contract.py
git commit -m "feat: add versioned per-user configuration"
```

---

### Task 5: 实现跨平台凭据管理

**Files:**
- Create: `src/zentao_ai/credentials/store.py`
- Create: `src/zentao_ai/credentials/environment.py`
- Create: `tests/unit/credentials/`

**Interfaces:**
- Produces: `CredentialStore.get(name: CredentialName) -> SecretStr | None`；`CredentialStore.set(name: CredentialName, value: SecretStr) -> None`；`resolve_credential(name, env, store, prompt) -> SecretStr`。

- [ ] **Step 1: 编写优先级和无泄漏测试**

断言 keyring 优先于环境变量，环境变量优先于临时输入；异常、日志、repr 和 doctor 输出不得包含秘密正文。

- [ ] **Step 2: 实现 keyring 与环境变量适配器**

服务名固定为 `zentao-ai-assistant`，键名只允许 `password`、`api-token`、`web-cookie`。

- [ ] **Step 3: 拒绝 YAML 明文秘密**

配置加载器检测 `password`、`token`、`cookie` 的明文值时返回字段级错误；`${ENV_NAME}` 引用允许通过。

- [ ] **Step 4: 运行测试并提交**

```powershell
python -m pytest tests/unit/credentials tests/unit/config -v
git add src/zentao_ai/credentials src/zentao_ai/config tests/unit
git commit -m "feat: add secure cross-platform credential storage"
```

---

### Task 6: 迁移 SQLite ledger、租约、checkpoint 和 outbox

**Files:**
- Create: `src/zentao_ai/state/models.py`
- Create: `src/zentao_ai/state/ledger.py`
- Create: `src/zentao_ai/state/outbox.py`
- Create: `src/zentao_ai/state/migrations.py`
- Create: `scripts/run-ledger.py`
- Create: `tests/unit/state/`
- Create: `tests/contract/test_run_ledger_compatibility.py`

**Interfaces:**
- Produces: `Ledger.acquire_lease(...) -> LeaseResult`、`record_comment(...)`、`get_comment(...)`、`put_outbox(...)`、`mark_outbox_result(...)`；兼容脚本保持原命令和 JSON 输出。

- [ ] **Step 1: 复制当前 `run-ledger.py` 到仓库作为黄金实现并建立等价测试**

同一输入分别调用用户级旧脚本和仓库兼容脚本，比较退出码及规范化 JSON。

- [ ] **Step 2: 为租约、幂等键和 UNKNOWN 对账编写测试**

覆盖同业务日期不可重入、过期租约、相同评论幂等、不同正文哈希不可复用、写入超时保持 UNKNOWN。

- [ ] **Step 3: 提取类到 `src/zentao_ai/state`**

SQLite schema 版本从 `1` 开始；迁移必须在事务中执行；数据库默认写入用户数据目录而非仓库。

- [ ] **Step 4: 将旧脚本改为兼容外壳**

`scripts/run-ledger.py` 只导入 `zentao_ai.state.cli:main`，保持原参数、退出码和 UTF-8 JSON。

- [ ] **Step 5: 运行等价测试并提交**

```powershell
python -m pytest tests/unit/state tests/contract/test_run_ledger_compatibility.py -v
git add src/zentao_ai/state scripts/run-ledger.py tests
git commit -m "refactor: migrate durable run ledger into shared core"
```

---

### Task 7: 迁移报告渲染并保持 v2 字节级兼容

**Files:**
- Create: `src/zentao_ai/reporting/models.py`
- Create: `src/zentao_ai/reporting/renderer.py`
- Modify: `scripts/render-report.py`
- Modify: `tests/test_render_report.py`
- Create: `tests/contract/test_report_v2_golden.py`

**Interfaces:**
- Produces: `render_personal(payload: Mapping[str, Any]) -> str`；`render_team(payload: Mapping[str, Any]) -> str`。

- [ ] **Step 1: 将现有 fixture 输出保存为黄金文件**

黄金文件使用 LF 和 UTF-8，无 BOM；个人和团队报告分别比较完整字符串。

- [ ] **Step 2: 把当前渲染函数移动到共享模块**

保持错误消息、字段校验、分组、中文标点、尾随换行和 `templateVersion=v2` 合同不变。

- [ ] **Step 3: 将旧脚本变成兼容入口**

`scripts/render-report.py` 调用 `zentao_ai.reporting.cli:main`，保留 `--mode personal|team`。

- [ ] **Step 4: 验证并提交**

```powershell
python -m pytest tests/test_render_report.py tests/contract/test_report_v2_golden.py -v
git add src/zentao_ai/reporting scripts/render-report.py tests
git commit -m "refactor: share deterministic v2 report renderer"
```

---

### Task 8: 迁移路由、Git 门禁和统一安全决策

**Files:**
- Create: `src/zentao_ai/routing/router.py`
- Create: `src/zentao_ai/repository/guard.py`
- Create: `src/zentao_ai/safety/actions.py`
- Create: `src/zentao_ai/safety/authorization.py`
- Create: `src/zentao_ai/safety/images.py`
- Create: `scripts/direct-branch-guard.py`
- Create: `tests/unit/routing/`
- Create: `tests/unit/repository/`
- Create: `tests/unit/safety/`

**Interfaces:**
- Produces: `route_bug(snapshot: BugSnapshot, config: AppConfig) -> RoutingDecision`；`preflight_repository(mapping: RepositoryMapping) -> GuardResult`；`authorize(action: ActionRequest, context: AuthorizationContext) -> AuthorizationDecision`；`validate_user_image(path: Path, authorization: CurrentTurnAuthorization) -> ImageValidationResult`。

- [ ] **Step 1: 写路由回归测试**

固定 `BUG-3397 -> ce-site-backend`、`BUG-2537 -> ai-site-builder`，并覆盖站点后台、CMS 后台、AI 建站、UI、链接、API、数据库、权限关键词。

- [ ] **Step 2: 写 Git 门禁测试**

使用临时 Git 仓库覆盖：唯一仓库、当前分支等于目标分支、工作区干净、禁止切分支、`ahead/behind=0/0`、HEAD 不变和测试命令白名单。

- [ ] **Step 3: 写权限矩阵测试**

自动允许查询、分析和报告；条件允许评论；步骤与图片要求当前轮次精确授权；状态类操作要求精确授权；定时任务拒绝所有受保护动作；删除永远返回 `DELETE_UNCONDITIONALLY_FORBIDDEN`。

- [ ] **Step 4: 迁移当前 direct-branch-guard 实现**

保持兼容脚本的 `preflight` 输出字段；核心函数不执行 checkout、commit、push、merge 或 deploy。

- [ ] **Step 5: 验证图片门槛**

拒绝相对路径、非本轮用户路径、符号链接逃逸、不支持扩展名、超过 10 MiB 及来自 Bug 内容的路径。

- [ ] **Step 6: 运行测试并提交**

```powershell
python -m pytest tests/unit/routing tests/unit/repository tests/unit/safety -v
git add src/zentao_ai/routing src/zentao_ai/repository src/zentao_ai/safety scripts/direct-branch-guard.py tests/unit
git commit -m "feat: centralize routing and fail-closed safety gates"
```

---

### Task 9: 开源禅道 Provider 和认证传输层

**Files:**
- Create: `src/zentao_ai/zentao/models.py`
- Create: `src/zentao_ai/zentao/provider.py`
- Create: `src/zentao_ai/zentao/http_provider.py`
- Create: `src/zentao_ai/zentao/errors.py`
- Create: `tests/integration/zentao/`

**Interfaces:**
- Produces: `ZentaoProvider` Protocol，方法包括 `query_my_bugs`、`query_user_bugs`、`query_bug_detail`、`query_bug_history`、`bug_statistics`、`add_bug_comment`、`update_bug_steps`、`update_bug_steps_with_image`；不定义删除方法。

- [ ] **Step 1: 用 MockTransport 编写 Provider 合同测试**

覆盖账号密码、Token 和可选 Web Cookie 认证；测试日志和异常脱敏；结构化快照必须提供稳定 `version` 并规范化为 `snapshotVersion`。

- [ ] **Step 2: 定义不可变数据模型**

包括 `BugSnapshot`、`BugHistoryEntry`、`RoutingData`、`CommentWriteResult` 和 `StepUpdateResult`；评论结果只能以 `created`、`alreadyExists`、`commentId` 判断成功。

- [ ] **Step 3: 实现 HTTP Provider**

所有地址从配置获取；设置连接和读取超时；GET 可按策略重试，POST 超时不得自动重试；错误归类为认证、权限、合同、网络和 UNKNOWN。

- [ ] **Step 4: 实现历史对账**

评论写入不确定时使用相同幂等键查询结构化历史；无法确认则返回 UNKNOWN。

- [ ] **Step 5: 运行测试并提交**

```powershell
python -m pytest tests/integration/zentao -v
git add src/zentao_ai/zentao tests/integration/zentao
git commit -m "feat: add open-source Zentao provider"
```

---

### Task 10: 实现完整个人、团队、评论、步骤和修复工作流

**Files:**
- Create: `src/zentao_ai/workflows/personal.py`
- Create: `src/zentao_ai/workflows/team_report.py`
- Create: `src/zentao_ai/workflows/analysis.py`
- Create: `src/zentao_ai/workflows/comments.py`
- Create: `src/zentao_ai/workflows/steps.py`
- Create: `src/zentao_ai/workflows/repair.py`
- Create: `src/zentao_ai/workflows/runtime.py`
- Create: `tests/unit/workflows/`
- Create: `tests/e2e/test_workflow_parity.py`

**Interfaces:**
- Produces: `run_personal(context: RunContext) -> PersonalRunResult`；`run_team_report(context: RunContext) -> TeamRunResult`；`analyze_bug(...) -> BugAnalysisResult`；`repair_bug(...) -> RepairResult`。

- [ ] **Step 1: 将 Skill 决策表转成参数化测试**

覆盖 `PROCEED_TO_EVIDENCE`、`FIX_CANDIDATE`、`NEEDS_REPORTER_INFO`、`NEEDS_ENGINEER_REVIEW`、`TOOL_OR_PERMISSION_GAP` 和 `PATCH_RETAINED_FOR_HUMAN_VALIDATION`。

- [ ] **Step 2: 实现个人和团队查询范围**

个人只读取 `personal.scopeNames`；团队只读取 `team.scopeNames` 和配置成员；团队流程强制只读；数量来自同一北京时区快照。

- [ ] **Step 3: 实现信息补充评论**

评论以真实 `@creator.account` 开头，经 v2 模板渲染；幂等键绑定规范正文 SHA-256；必须在创建者、快照、历史、冷却期和权限全部通过后写入。

- [ ] **Step 4: 实现步骤与图片更新**

只替换完整复现步骤，不修改其他字段；调用前再次执行授权和图片检查；个人/团队日报及定时任务永远不调用。

- [ ] **Step 5: 实现受控修复流程**

顺序固定为仓库门禁、失败复现、最小补丁、白名单测试、diff 检查、最新快照复核、FINAL_DECISION。测试失败保留 AI postimage 供人工验证，但不得返回 FIX_CANDIDATE 或发布成功评论。

- [ ] **Step 6: 验证单 Bug 隔离和失败关闭**

一个 Bug 失败后继续处理无关 Bug；截断和成员失败只能生成部分完成报告；未知不得计入成功。

- [ ] **Step 7: 运行全工作流测试并提交**

```powershell
python -m pytest tests/unit/workflows tests/e2e/test_workflow_parity.py -v
git add src/zentao_ai/workflows tests
git commit -m "feat: implement complete shared Zentao workflows"
```

---

### Task 11: 交付 CLI、初始化、doctor 和 dry-run

**Files:**
- Create: `src/zentao_ai/cli/app.py`
- Create: `src/zentao_ai/cli/config_commands.py`
- Create: `src/zentao_ai/cli/auth_commands.py`
- Create: `src/zentao_ai/cli/bug_commands.py`
- Create: `src/zentao_ai/cli/report_commands.py`
- Create: `src/zentao_ai/cli/doctor.py`
- Create: `tests/e2e/cli/`

**Interfaces:**
- Produces: `zentao-ai config init`、`auth login`、`doctor`、`bugs mine`、`bugs user`、`report personal`、`report team`、`bug analyze`、`bug update-steps`、`bug update-steps-with-image`、`repair`、`run --dry-run`。

- [ ] **Step 1: 编写 Typer CliRunner 失败测试**

覆盖命令帮助、退出码 0/2/3、JSON 可选输出、非交互模式、秘密不回显和取消操作无副作用。

- [ ] **Step 2: 实现 `config init` 和 `auth login`**

配置初始化采用原子写入；已存在文件默认拒绝覆盖；认证输入使用隐藏提示并写入 keyring。

- [ ] **Step 3: 实现 `doctor`**

按配置、凭据、连接、权限、仓库、分支、测试、MCP、报告目录输出 PASS/FAIL；失败原因脱敏，任一强制项失败返回退出码 2。

- [ ] **Step 4: 实现业务命令和 dry-run**

dry-run 输出将调用的精确 MCP/Provider 工具、参数字段和顺序，标记“仅计划、未执行”，不得获取写租约或写 outbox。

- [ ] **Step 5: 运行 CLI 测试并提交**

```powershell
python -m pytest tests/e2e/cli -v
zentao-ai --help
git add src/zentao_ai/cli tests/e2e/cli pyproject.toml
git commit -m "feat: deliver safe standalone Zentao CLI"
```

---

### Task 12: 交付内置 MCP Server 并保持工具合同

**Files:**
- Create: `src/zentao_ai/mcp_server/server.py`
- Create: `src/zentao_ai/mcp_server/tools.py`
- Create: `src/zentao_ai/mcp_server/schemas.py`
- Create: `tests/contract/test_mcp_tools.py`
- Create: `tests/e2e/test_mcp_stdio.py`

**Interfaces:**
- Produces: `zentao-ai mcp serve`；完整工具注册名保持 `mcp__zentao__<tool>` 语义。

- [ ] **Step 1: 编写工具清单合同测试**

断言只读工具、`add_bug_comment`、两个步骤更新工具存在；断言 `delete_bug`、`remove_bug` 和任何等价永久删除工具不存在。

- [ ] **Step 2: 实现 stdio MCP Server**

工具仅验证协议参数并调用共享工作流；所有返回包含 `structuredContent`；稳定版本输出为 `version`，核心内部规范化为 `snapshotVersion`。

- [ ] **Step 3: 实现写工具参数合同**

评论要求 `bugId`、`comment`、`confirm:true`、非空 `idempotencyKey`；步骤更新要求当前轮次授权上下文；图片路径不得从 Bug 数据推导。

- [ ] **Step 4: 运行 MCP 测试并提交**

```powershell
python -m pytest tests/contract/test_mcp_tools.py tests/e2e/test_mcp_stdio.py -v
git add src/zentao_ai/mcp_server tests
git commit -m "feat: ship compatible built-in Zentao MCP server"
```

---

### Task 13: 打包 Codex 插件和团队 Marketplace

**Files:**
- Create: `plugins/zentao-ai-bug/.codex-plugin/plugin.json`
- Create: `plugins/zentao-ai-bug/.mcp.json`
- Create: `plugins/zentao-ai-bug/scripts/`
- Create: `.agents/plugins/marketplace.json`
- Modify: `plugins/zentao-ai-bug/skills/zentao-ai-bug/SKILL.md`
- Create: `tests/contract/test_plugin_package.py`

**Interfaces:**
- Produces: 可由 Codex 安装的 `zentao-ai-bug` 插件，MCP command 为 `zentao-ai mcp serve`。

- [ ] **Step 1: 使用 plugin-creator 脚本建立标准 manifest 和团队 Marketplace**

从 plugin-creator 技能目录运行 scaffold/validate 工具，插件名固定 `zentao-ai-bug`；Marketplace entry 使用 `AVAILABLE`、`ON_INSTALL`、`Productivity`。

- [ ] **Step 2: 合并已经冻结的 Skill 文件**

保留全部安全合同，只将脚本路径改成插件内兼容路径或已安装 CLI；不得削弱删除禁令、精确授权、图片来源、快照复核或定时任务限制。

- [ ] **Step 3: 配置 MCP 启动**

`.mcp.json` 只传配置路径提示，不嵌入账号、密码、Token 或 Cookie。

- [ ] **Step 4: 验证插件**

```powershell
python C:\Users\wwtlove66\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\zentao-ai-bug
python -m pytest tests/contract/test_plugin_package.py tests/test_skill_contract.py tests/test_zentao_skill_contract.py -v
```

预期：插件验证和全部 Skill 合同通过。

- [ ] **Step 5: 提交插件**

```powershell
git add plugins .agents/plugins/marketplace.json tests
git commit -m "feat: package full Zentao assistant Codex plugin"
```

---

### Task 14: 实现跨平台定时任务且保持团队任务只读

**Files:**
- Create: `src/zentao_ai/scheduling/models.py`
- Create: `src/zentao_ai/scheduling/windows.py`
- Create: `src/zentao_ai/scheduling/macos.py`
- Create: `src/zentao_ai/scheduling/linux.py`
- Create: `src/zentao_ai/scheduling/service.py`
- Create: `tests/unit/scheduling/`

**Interfaces:**
- Produces: `install_schedule(config: AppConfig, mode: ScheduleMode) -> InstallResult`；`uninstall_schedule(name: str) -> UninstallResult`。

- [ ] **Step 1: 编写平台命令生成测试**

Windows 使用 Task Scheduler XML，macOS 使用 launchd plist，Linux 使用 systemd user timer；三者均每天本地时间 08:00 运行。

- [ ] **Step 2: 实现补跑语义**

4 小时内延迟标记补跑；超过 24 小时只生成缺失摘要；不得逐日重放。

- [ ] **Step 3: 强制团队和所有定时任务的写保护**

生成命令必须带 `--non-interactive`；团队使用 `report team`；个人定时任务也不得执行步骤更新、状态变更或其他受保护操作。

- [ ] **Step 4: 运行测试并提交**

```powershell
python -m pytest tests/unit/scheduling tests/test_automation_contract.py -v
git add src/zentao_ai/scheduling tests
git commit -m "feat: add safe cross-platform daily scheduling"
```

---

### Task 15: 文档、开源治理和 CI

**Files:**
- Rewrite: `README.md`
- Create: `LICENSE`
- Create: `SECURITY.md`
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`
- Create: `docs/installation.md`
- Create: `docs/configuration.md`
- Create: `docs/security-model.md`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`
- Create: `.github/dependabot.yml`

**Interfaces:**
- Produces: 可复现安装、配置、开发、报告漏洞、发布和回滚流程。

- [ ] **Step 1: 编写用户文档**

README 明确非禅道官方项目、功能清单、CLI/插件安装、三分钟 quickstart、凭据规则、禁止删除和 Windows 首验状态。

- [ ] **Step 2: 添加 Apache-2.0 和安全政策**

SECURITY.md 要求通过 GitHub Security Advisory 私下报告，不得在 Issue 中发送真实 Bug、凭据或客户数据。

- [ ] **Step 3: 添加三平台 CI**

矩阵为 `windows-latest`、`macos-latest`、`ubuntu-latest` 和 Python 3.11/3.12/3.13；执行 pytest、ruff、mypy、build、twine check、插件验证和秘密扫描。

- [ ] **Step 4: 添加发布工作流**

仅 `v*` tag 触发；先执行全套 CI，再构建 wheel/sdist、生成 SHA-256、创建 GitHub Release；PyPI 使用 Trusted Publishing，不保存长期 Token。

- [ ] **Step 5: 运行本地文档及全套检查并提交**

```powershell
python -m pytest -v
python -m ruff check src tests
python -m mypy src
python -m build
python -m twine check dist\*
git add README.md LICENSE SECURITY.md CONTRIBUTING.md CHANGELOG.md docs .github
git commit -m "docs: prepare secure cross-platform open-source release"
```

---

### Task 16: 真实环境验收、GitHub 发布和回滚验证

**Files:**
- Create: `docs/release-checklist.md`
- Create: `docs/acceptance/windows-0.1.0.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: GitHub 仓库、`v0.1.0` Release、PyPI 包、可分享 Codex 插件及脱敏验收记录。

- [ ] **Step 1: 重新验证 GitHub 安全登录**

```powershell
gh auth status
```

预期：显示正确 GitHub 账号和 HTTPS Git 权限；若失败，运行 `gh auth login --web`，不得在聊天、脚本或文件中输入 Token。

- [ ] **Step 2: 执行发布前秘密和历史扫描**

检查工作树、暂存区和全部提交历史；任何真实账号、域名、密码、Token、Cookie、成员或报告命中都必须先清理，禁止带病推送。

- [ ] **Step 3: 在 Windows 测试禅道执行验收**

依次执行 `doctor`、个人查询、团队只读报告、dry-run、受控评论、步骤更新、图片更新、路由、代码修复失败路径、代码修复成功候选路径、超时 UNKNOWN 对账和定时任务安装/卸载。验收文档只记录脱敏 ID 和 PASS/FAIL。

- [ ] **Step 4: 创建 GitHub 仓库并首次推送**

建议仓库名 `zentao-ai-assistant`：

```powershell
gh repo create wwtweiwenting/zentao-ai-assistant --public --source . --remote origin --description "Open-source Zentao AI assistant for Codex and CLI"
git push -u origin main
```

预期：公共仓库创建成功，GitHub secret scanning 无告警。

- [ ] **Step 5: 验证安装和回滚**

在干净虚拟环境安装 wheel，验证 CLI；安装 Marketplace 插件，验证 MCP；再降级到上一构建并确认配置和 ledger 可读。

- [ ] **Step 6: 发布 0.1.0**

```powershell
git tag -s v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

预期：CI 全绿、GitHub Release 创建、PyPI Trusted Publishing 成功、插件可安装。

- [ ] **Step 7: 完成发布记录**

```powershell
git add docs/release-checklist.md docs/acceptance/windows-0.1.0.md CHANGELOG.md
git commit -m "docs: record v0.1.0 acceptance and release"
git push
```

---

## 最终验收清单

- [ ] 当前遗留测试和新测试全部通过。
- [ ] CLI、MCP、Codex 插件对相同输入产生同一安全决策。
- [ ] 所有当前功能均在 `test_legacy_feature_inventory.py` 中有对应验证。
- [ ] 删除工具未注册且核心无删除接口。
- [ ] 团队报告和全部定时任务不产生受保护写操作。
- [ ] 报告与 `templateVersion=v2` 黄金文件一致。
- [ ] 配置、凭据、日志、异常和 doctor 输出均完成脱敏。
- [ ] Windows 真实环境验收通过，macOS/Linux CI 通过。
- [ ] wheel、sdist、Codex 插件和 Marketplace 均通过验证。
- [ ] GitHub 仓库和历史不包含任何真实秘密或业务数据。
- [ ] 安装、升级、降级和回滚步骤均经过验证。
