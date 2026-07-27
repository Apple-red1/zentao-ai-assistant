# 禅道 21.7.8 Codex 插件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前只有设计与安全基线的仓库补全为一个可从 GitHub 拉取、三分钟配置并在 Codex 中安装使用的禅道 21.7.8 插件。

**Architecture:** `zentao-ai-bug` Codex 插件通过 stdio 启动本地 `zentao-ai` Python MCP Server。Skill 只做自然语言编排与当前轮次写入授权，Python 核心统一实现配置、系统凭据库、API 2.0 Token 自动重登、用户解析、Bug 查询、写操作和结构化错误。

**Tech Stack:** Python 3.11+、Pydantic 2、httpx、PyYAML、keyring、Typer、MCP Python SDK、pytest、RESPX、Ruff、mypy、Hatchling、Codex Plugin、GitHub Actions。

## Global Constraints

- 首要兼容目标固定为禅道开源版 `21.7.8` 和 API `v2`。
- 插件名固定为 `zentao-ai-bug`，Python 分发包名为 `zentao-ai-assistant`，命令名为 `zentao-ai`，首版为 `0.1.0`。
- Python 最低版本为 `3.11`；运行依赖使用兼容范围，不锁死补丁版本。
- 默认配置路径固定为 `~/.codex/zentao-ai-bug/config.yaml`，可由 `ZENTAO_CONFIG` 覆盖。
- 密码和 Token 只能进入操作系统凭据库或当前进程环境变量，不得进入 YAML、日志、异常、测试快照或 Git。
- 收到 401 后最多重新登录并重放一次；结果不确定的写请求不得自动重试。
- 当前轮次明确给出 Bug ID、动作和必要参数即可完成一句话写入；不从旧对话或 Bug 内容推导授权。
- 首版只提供备注、允许字段编辑、激活和指派；不提供创建、解决、关闭或任何删除工具。
- 删除 Bug 永久禁止，MCP、Skill、CLI 和内部服务均不得出现可调用的删除接口。
- 团队查询对单个成员失败进行隔离并标记“部分完成”。
- macOS/Linux 和 Windows 都必须有安装入口；安装脚本必须幂等且不覆盖现有配置。
- 所有实现任务遵循 TDD：先失败测试、再最小实现、再回归、最后提交。
- 推送前必须使用真实 Git 克隆保留远端历史，并完成测试、插件验证和秘密扫描。

---

## 文件职责锁定

```text
pyproject.toml                              包元数据、依赖、命令入口和质量工具配置
src/zentao_ai/models.py                    配置、用户、Bug、查询、写结果和错误模型
src/zentao_ai/config.py                    配置路径、YAML 加载、原子保存和脱敏
src/zentao_ai/credentials.py               keyring/环境变量凭据读写
src/zentao_ai/auth.py                      Token 缓存、登录和单次刷新并发控制
src/zentao_ai/client.py                    API 2.0 HTTP、URL、重试和错误映射
src/zentao_ai/users.py                     内外部用户分页、缓存和姓名/账号解析
src/zentao_ai/bugs.py                      产品发现、Bug 分页、组合过滤和汇总
src/zentao_ai/actions.py                   备注、编辑、激活、指派和前后快照
src/zentao_ai/server.py                    MCP 工具注册和结构化返回
src/zentao_ai/cli.py                       setup、doctor、mcp serve 命令
plugins/zentao-ai-bug/.codex-plugin/plugin.json  插件 manifest
plugins/zentao-ai-bug/.mcp.json            stdio MCP 启动配置
plugins/zentao-ai-bug/skills/zentao-ai-bug/SKILL.md  自然语言与安全编排
.agents/plugins/marketplace.json           仓库 Marketplace
scripts/install.sh                         macOS/Linux 三分钟安装
scripts/install.ps1                        Windows 三分钟安装
README.md                                  首屏快速开始和常用示例
docs/*.md                                  详细安装、配置、功能、安全和排错
tests/unit/                                纯逻辑测试
tests/integration/                         模拟禅道 HTTP 合同
tests/contract/                            插件、Skill、文档和仓库合同
tests/e2e/                                 CLI、MCP 与安装冒烟测试
```

---

### Task 1: 建立真实 Git 工作分支与可安装 Python 包

**Files:**
- Create: `pyproject.toml`
- Create: `src/zentao_ai/__init__.py`
- Create: `src/zentao_ai/__main__.py`
- Create: `src/zentao_ai/py.typed`
- Create: `tests/unit/test_package_metadata.py`
- Preserve: `docs/superpowers/specs/2026-07-27-zentao-codex-plugin-design.md`
- Preserve: `docs/superpowers/plans/2026-07-27-zentao-codex-plugin-implementation.md`

**Interfaces:**
- Consumes: 远端 `wwtweiwenting/zentao-ai-assistant` 默认分支及本设计/计划。
- Produces: `zentao_ai.__version__: str`、控制台入口 `zentao-ai = zentao_ai.cli:app`、分支 `codex/zentao-plugin-v0.1`。

- [ ] **Step 1: 取得真实 Git 工作副本**

通过 GitHub CLI 网页授权登录，不在聊天或文件中输入 Token；验证 `gh auth status` 后克隆远端。若本机尚无 `gh`，通过 Homebrew 安装官方 GitHub CLI，再执行网页授权。

```bash
gh auth login --web --git-protocol https
gh auth status
git clone https://github.com/wwtweiwenting/zentao-ai-assistant.git zentao-ai-assistant-git
cd zentao-ai-assistant-git
git switch -c codex/zentao-plugin-v0.1
git log -5 --oneline
```

预期：显示正确 GitHub 账号和现有提交历史；不得在下载快照上执行强制推送。

- [ ] **Step 2: 将已确认设计和计划带入真实分支**

使用补丁方式加入两个 2026-07-27 文档，运行：

```bash
git status --short
git diff --check
```

预期：仅出现两个新文档，没有旧文件被覆盖。

- [ ] **Step 3: 编写失败的包元数据测试**

```python
from importlib.metadata import metadata

import zentao_ai


def test_package_identity() -> None:
    package = metadata("zentao-ai-assistant")
    assert package["Version"] == "0.1.0"
    assert zentao_ai.__version__ == "0.1.0"
```

运行：

```bash
python3 -m pytest tests/unit/test_package_metadata.py -v
```

预期：FAIL，`zentao_ai` 尚不存在。

- [ ] **Step 4: 创建最小包和依赖边界**

`pyproject.toml` 使用 Hatchling 和 `src` 布局；运行依赖固定为：

```toml
dependencies = [
  "httpx>=0.27,<1",
  "keyring>=25,<26",
  "mcp>=1,<2",
  "pydantic>=2.7,<3",
  "PyYAML>=6,<7",
  "typer>=0.12,<1",
]

[project.optional-dependencies]
dev = [
  "build>=1,<2",
  "mypy>=1.10,<2",
  "pytest>=8,<9",
  "pytest-cov>=5,<7",
  "respx>=0.21,<1",
  "ruff>=0.6,<1",
  "twine>=5,<7",
  "types-PyYAML>=6,<7",
]

[project.scripts]
zentao-ai = "zentao_ai.cli:app"
```

`src/zentao_ai/__init__.py` 只导出 `__version__ = "0.1.0"`，`__main__.py` 调用 `cli.app()`。

- [ ] **Step 5: 安装开发环境并验证包**

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest tests/unit/test_package_metadata.py -v
python3 -m build
python3 -m twine check dist/*
```

预期：测试、wheel、sdist 和 twine 检查全部通过。

- [ ] **Step 6: 提交包骨架**

```bash
git add pyproject.toml src tests/unit docs/superpowers
git commit -m "build: establish installable Zentao plugin package"
```

---

### Task 2: 实现版本化配置、凭据存储与脱敏

**Files:**
- Create: `src/zentao_ai/models.py`
- Create: `src/zentao_ai/config.py`
- Create: `src/zentao_ai/credentials.py`
- Create: `config/zentao.example.yaml`
- Create: `tests/unit/test_config.py`
- Create: `tests/unit/test_credentials.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `Settings`、`TeamMember`、`QueryDefaults`、`WriteSettings`、`load_settings(path: Path | None = None) -> Settings`、`save_settings(settings: Settings, path: Path | None = None) -> Path`、`redact(value: object) -> object`、`CredentialStore` Protocol、`KeyringCredentialStore`。

- [ ] **Step 1: 编写配置和凭据失败测试**

```python
def test_config_never_accepts_plaintext_password(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("version: 1\nzentao:\n  base_url: https://z.example\n  account: me\n  password: secret\n")
    with pytest.raises(ConfigError, match="password"):
        load_settings(path)


def test_keyring_keys_are_scoped_by_url_and_account(fake_keyring: FakeKeyring) -> None:
    store = KeyringCredentialStore(backend=fake_keyring)
    store.set_password("https://z.example", "me", "secret")
    assert store.get_password("https://z.example", "me") == "secret"
    assert store.get_password("https://other.example", "me") is None
```

运行：

```bash
python3 -m pytest tests/unit/test_config.py tests/unit/test_credentials.py -v
```

预期：FAIL，模型和存储尚不存在。

- [ ] **Step 2: 定义严格配置模型**

`models.py` 定义：

```python
class TeamMember(BaseModel):
    name: str
    account: str

class ZentaoSettings(BaseModel):
    base_url: AnyHttpUrl
    api_version: Literal["v2"] = "v2"
    account: str

class QueryDefaults(BaseModel):
    default_status: Literal["unresolved", "active", "resolved", "closed", "all"] = "unresolved"
    page_size: int = Field(default=100, ge=1, le=1000)
    max_results: int = Field(default=500, ge=1, le=5000)

class WriteSettings(BaseModel):
    enabled: bool = True

class TeamSettings(BaseModel):
    members: list[TeamMember] = Field(default_factory=list)

class Settings(BaseModel):
    version: Literal[1]
    zentao: ZentaoSettings
    team: TeamSettings = Field(default_factory=TeamSettings)
    query: QueryDefaults = Field(default_factory=QueryDefaults)
    writes: WriteSettings = Field(default_factory=WriteSettings)
```

模型使用 `extra="forbid"`，明确拒绝 `password`、`token` 和未知字段。

- [ ] **Step 3: 实现配置路径、原子保存和脱敏**

`default_config_path()` 返回 `Path.home() / ".codex" / "zentao-ai-bug" / "config.yaml"`。`load_settings` 优先使用显式参数，再读取 `ZENTAO_CONFIG`，最后使用默认路径。`save_settings` 写入同目录临时文件、权限设为 `0600`，再用 `os.replace` 原子替换。

`redact` 递归替换键名包含 `password`、`token`、`cookie`、`authorization` 的值为 `"<redacted>"`。

- [ ] **Step 4: 实现 keyring 与环境变量回退**

```python
class CredentialStore(Protocol):
    def get_password(self, base_url: str, account: str) -> str | None: ...
    def set_password(self, base_url: str, account: str, password: str) -> None: ...
    def get_token(self, base_url: str, account: str) -> str | None: ...
    def set_token(self, base_url: str, account: str, token: str) -> None: ...
    def delete_token(self, base_url: str, account: str) -> None: ...
```

服务名固定为 `zentao-ai-bug`，用户名键包含规范化 URL 和账号。密码读取顺序为 keyring、`ZENTAO_PASSWORD`；Token 只从 keyring 读取。错误文本不得包含秘密值。

- [ ] **Step 5: 添加示例、忽略规则并运行测试**

`config/zentao.example.yaml` 使用 `https://zentao.example.com`、`my-account`、张三/李四占位账号；`.gitignore` 增加所有项目内本地配置变体但不忽略示例。

```bash
python3 -m pytest tests/unit/test_config.py tests/unit/test_credentials.py tests/contract/test_repository_hygiene.py -v
python3 -m ruff check src tests
python3 -m mypy src
```

预期：全部通过，无明文秘密命中。

- [ ] **Step 6: 提交配置与凭据层**

```bash
git add .gitignore config src/zentao_ai/models.py src/zentao_ai/config.py src/zentao_ai/credentials.py tests
git commit -m "feat: add safe local configuration and credentials"
```

---

### Task 3: 实现 API 2.0 登录、Token 自动重登与 HTTP 错误模型

**Files:**
- Create: `src/zentao_ai/errors.py`
- Create: `src/zentao_ai/auth.py`
- Create: `src/zentao_ai/client.py`
- Create: `tests/unit/test_auth.py`
- Create: `tests/integration/test_client.py`

**Interfaces:**
- Consumes: `Settings`、`CredentialStore`。
- Produces: `ErrorCode`、`ZentaoError`、`AuthManager.get_token(force_refresh: bool = False) -> str`、`ZentaoClient.request_json(method, path, *, params=None, json=None, write=False) -> dict[str, Any]`。

- [ ] **Step 1: 编写 401 自动重登和写超时失败测试**

```python
@pytest.mark.anyio
async def test_401_refreshes_once_and_replays_request(respx_mock, client) -> None:
    route = respx_mock.get("https://z.example/api.php/v2/users").mock(
        side_effect=[Response(401), Response(200, json={"status": "success", "users": []})]
    )
    login = respx_mock.post("https://z.example/api.php/v2/users/login").mock(
        return_value=Response(200, json={"status": "success", "token": "fresh"})
    )
    assert await client.request_json("GET", "/users") == {"status": "success", "users": []}
    assert route.call_count == 2
    assert login.call_count == 1


@pytest.mark.anyio
async def test_write_timeout_is_unknown_and_not_retried(respx_mock, client) -> None:
    route = respx_mock.put("https://z.example/api.php/v2/bugs/1").mock(side_effect=httpx.ReadTimeout("late"))
    with pytest.raises(ZentaoError) as exc:
        await client.request_json("PUT", "/bugs/1", json={"title": "x"}, write=True)
    assert exc.value.code is ErrorCode.UNKNOWN_WRITE_RESULT
    assert route.call_count == 1
```

- [ ] **Step 2: 定义稳定错误代码**

`ErrorCode` 固定包含 `CONFIG_ERROR`、`AUTH_ERROR`、`PERMISSION_DENIED`、`USER_NOT_FOUND`、`USER_AMBIGUOUS`、`BUG_NOT_FOUND`、`VALIDATION_ERROR`、`CAPABILITY_UNAVAILABLE`、`NETWORK_ERROR`、`UNKNOWN_WRITE_RESULT`。`ZentaoError` 保存 `code`、脱敏 `message`、`retryable` 和可选 `details`。

- [ ] **Step 3: 实现登录和并发刷新锁**

`AuthManager` 使用 `asyncio.Lock`。登录固定调用 `POST /api.php/v2/users/login`，请求体为账号密码；响应必须满足 `status == "success"` 且 token 非空。`force_refresh=True` 时删除旧 Token；并发 401 只能触发一次实际登录。

- [ ] **Step 4: 实现 HTTP 客户端**

规范化 `base_url`，只允许同源拼接 `/api.php/v2`。默认连接超时 10 秒、读取超时 30 秒、TLS 校验开启。请求加 `Token` 头；401 刷新一次；403 映射权限错误；404 映射对象不存在；其他 4xx 映射校验错误；读请求仅对连接错误、429 和 5xx 最多重试两次，退避 0.2/0.5 秒。

- [ ] **Step 5: 运行认证和 HTTP 测试**

```bash
python3 -m pytest tests/unit/test_auth.py tests/integration/test_client.py -v
python3 -m ruff check src tests
python3 -m mypy src
```

预期：401 只登录一次、写超时不重试、错误中无密码或 Token。

- [ ] **Step 6: 提交认证传输层**

```bash
git add src/zentao_ai/auth.py src/zentao_ai/client.py src/zentao_ai/errors.py tests
git commit -m "feat: add resilient Zentao API authentication"
```

---

### Task 4: 实现内部、外部与团队用户解析

**Files:**
- Modify: `src/zentao_ai/models.py`
- Create: `src/zentao_ai/users.py`
- Create: `tests/unit/test_users.py`
- Create: `tests/integration/test_users_api.py`

**Interfaces:**
- Produces: `UserRef(id: str, account: str, real_name: str, kind: Literal["inside", "outside"])`、`UserDirectory.list_users(kind="all") -> list[UserRef]`、`UserDirectory.resolve(query: str, kind="all") -> UserRef`、`UserDirectory.validate_team(members: list[TeamMember]) -> TeamValidationResult`。

- [ ] **Step 1: 编写账号、姓名、重名和外部人员测试**

```python
def test_resolve_prefers_exact_account(directory: UserDirectory) -> None:
    assert directory.resolve_cached("zhangsan").account == "zhangsan"


def test_duplicate_real_name_is_ambiguous(directory: UserDirectory) -> None:
    with pytest.raises(ZentaoError) as exc:
        directory.resolve_cached("张三")
    assert exc.value.code is ErrorCode.USER_AMBIGUOUS
    assert {item["account"] for item in exc.value.details["candidates"]} == {"zhangsan", "zhangsan2"}


@pytest.mark.anyio
async def test_outside_user_can_be_resolved_without_team_config(directory: UserDirectory) -> None:
    user = await directory.resolve("external-a", kind="outside")
    assert user.kind == "outside"
```

- [ ] **Step 2: 实现用户分页读取**

分别调用 `GET /users?browseType=inside` 和 `GET /users?browseType=outside`，`recPerPage=1000`，从第 1 页读取到总页数。缓存只在 MCP 进程内存在，TTL 为 5 分钟；写操作前强制刷新目标用户。

- [ ] **Step 3: 实现确定性匹配顺序**

严格按照账号精确、姓名精确、不区分大小写账号匹配。零候选抛 `USER_NOT_FOUND`，多候选抛 `USER_AMBIGUOUS` 并只返回账号、姓名和内外部类型。

- [ ] **Step 4: 实现团队配置验证**

逐个成员解析；账号和姓名都给出时必须指向同一用户。成功项返回规范账号；失败项单独记录，不能让整个团队验证崩溃。

- [ ] **Step 5: 运行测试并提交**

```bash
python3 -m pytest tests/unit/test_users.py tests/integration/test_users_api.py -v
git add src/zentao_ai/models.py src/zentao_ai/users.py tests
git commit -m "feat: resolve internal external and team users"
```

---

### Task 5: 实现 Bug 分页、组合过滤和汇总

**Files:**
- Modify: `src/zentao_ai/models.py`
- Create: `src/zentao_ai/bugs.py`
- Create: `tests/unit/test_bug_filters.py`
- Create: `tests/unit/test_bug_summary.py`
- Create: `tests/integration/test_bug_queries.py`

**Interfaces:**
- Produces: `BugFilters`、`BugRecord`、`BugQueryResult`、`BugService.get_bug(bug_id: int) -> BugRecord`、`BugService.query_my_bugs(filters) -> BugQueryResult`、`BugService.query_user_bugs(user, filters) -> BugQueryResult`、`BugService.query_team_bugs(users, filters) -> BugQueryResult`、`BugService.search_bugs(filters) -> BugQueryResult`。

- [ ] **Step 1: 编写过滤和分页失败测试**

```python
def test_filters_can_be_combined(sample_bugs: list[BugRecord]) -> None:
    filters = BugFilters(status="unresolved", assigned_to=["zhangsan"], severity=[1], keyword="登录")
    assert [bug.id for bug in apply_filters(sample_bugs, filters)] == [101]


@pytest.mark.anyio
async def test_query_reads_every_page_until_limit(service, fake_api) -> None:
    result = await service.search_bugs(BugFilters(product_id=3, max_results=250))
    assert len(result.bugs) == 250
    assert fake_api.requested_pages == [1, 2, 3]
    assert result.truncated is True
```

- [ ] **Step 2: 定义查询模型**

`BugFilters` 包含 `status`、`assigned_to`、`opened_by`、`product_id`、`project_id`、`execution_id`、`priority`、`severity`、`bug_type`、`keyword`、`opened_after/before`、`edited_after/before`、`order_by`、`max_results`。数值 ID 必须大于零，日期使用带时区的 ISO 8601。

- [ ] **Step 3: 实现范围规划与分页**

存在 `product_id` 时调用 `/products/{id}/bugs`；存在 `project_id` 时调用 `/projects/{id}/bugs`；存在 `execution_id` 时调用 `/executions/{id}/bugs`。无范围时先分页读取当前账号可见产品，再逐产品读取 Bug。服务端使用 `browseType=unresolved` 或 `all`，其余条件在规范化后的本地模型上执行。

- [ ] **Step 4: 实现个人、团队和外部用户查询**

个人查询把 `assigned_to` 固定为配置账号；指定人员查询先经 `UserDirectory.resolve`；团队查询用并发上限 5 逐成员执行，并把失败成员放入 `partial_failures`。同一 Bug 不重复计数。

- [ ] **Step 5: 实现汇总**

结果包含 `total`、`by_status`、`by_assignee`、`by_priority`、`by_severity`、`bugs`、`truncated`、`partial_failures`。所有映射键按稳定顺序输出，便于 Codex 和快照测试。

- [ ] **Step 6: 运行查询测试并提交**

```bash
python3 -m pytest tests/unit/test_bug_filters.py tests/unit/test_bug_summary.py tests/integration/test_bug_queries.py -v
git add src/zentao_ai/models.py src/zentao_ai/bugs.py tests
git commit -m "feat: add flexible Zentao bug queries"
```

---

### Task 6: 实现受控备注、编辑、激活和指派

**Files:**
- Modify: `src/zentao_ai/models.py`
- Create: `src/zentao_ai/actions.py`
- Create: `tests/unit/test_action_guards.py`
- Create: `tests/integration/test_bug_actions.py`

**Interfaces:**
- Produces: `BugChanges`、`WriteAuthorization`、`BugWriteResult`、`BugActionService.add_comment`、`edit_bug`、`activate_bug`、`assign_bug`；不产生任何删除方法。

- [ ] **Step 1: 编写写入守卫失败测试**

```python
def test_write_requires_current_turn_authorization(service: BugActionService) -> None:
    with pytest.raises(ZentaoError) as exc:
        service.validate_authorization(WriteAuthorization(confirm=False, bug_id=123, action="assign"))
    assert exc.value.code is ErrorCode.VALIDATION_ERROR


def test_delete_is_not_an_action() -> None:
    assert "delete_bug" not in dir(BugActionService)
    assert "remove_bug" not in dir(BugActionService)
```

- [ ] **Step 2: 定义编辑白名单和写入结果**

`BugChanges` 只允许 `title`、`severity`、`priority`、`bug_type`、`opened_builds`、`steps`、`project_id`、`execution_id`、`story_id`。`WriteAuthorization` 要求 `confirm is True`、Bug ID 与动作一致。`BugWriteResult` 包含 `status`、`before`、`after`、`changed_fields` 和 `message`。

- [ ] **Step 3: 实现编辑和独立备注**

编辑固定调用 `PUT /bugs/{id}`。备注先 `GET /bugs/{id}`，从最新对象读取 `title` 和 `openedBuild`，提交：

```python
payload = {
    "title": before.title,
    "openedBuild": before.opened_build_ids,
    "comment": comment,
}
```

不得提交空标题、空版本或其他旧字段；写后重新读取详情并验证动作列表新增备注。

- [ ] **Step 4: 实现激活和指派**

激活调用 `PUT /bugs/{id}/activate`，只允许原状态 `resolved` 或 `closed`，参数为 `openedBuild`、可选 `assignedTo` 和 `comment`。指派调用 `PUT /bugs/{id}/assignTo`，先刷新用户目录并提交 `assignedTo` 与可选 `comment`；关闭状态 Bug 禁止指派。

- [ ] **Step 5: 覆盖不确定结果和前后快照**

写超时返回 `UNKNOWN_WRITE_RESULT`，不二次发送；随后只读查询用于展示最新状态，但不能把匹配状态当作确定写成功。正常写入要求后快照字段与请求一致，否则返回 `CAPABILITY_UNAVAILABLE`。

- [ ] **Step 6: 运行写入测试并提交**

```bash
python3 -m pytest tests/unit/test_action_guards.py tests/integration/test_bug_actions.py -v
git add src/zentao_ai/models.py src/zentao_ai/actions.py tests
git commit -m "feat: add guarded Zentao bug actions"
```

---

### Task 7: 暴露稳定 MCP 工具合同

**Files:**
- Create: `src/zentao_ai/server.py`
- Create: `tests/contract/test_mcp_tools.py`
- Create: `tests/e2e/test_mcp_stdio.py`

**Interfaces:**
- Consumes: `BugService`、`BugActionService`、`UserDirectory`、`Settings`。
- Produces: stdio MCP Server 和工具 `query_my_bugs`、`query_team_bugs`、`query_user_bugs`、`search_bugs`、`get_bug`、`list_users`、`add_bug_comment`、`edit_bug`、`activate_bug`、`assign_bug`。

- [ ] **Step 1: 编写工具清单和删除禁令合同**

```python
EXPECTED = {
    "query_my_bugs", "query_team_bugs", "query_user_bugs", "search_bugs",
    "get_bug", "list_users", "add_bug_comment", "edit_bug", "activate_bug", "assign_bug",
}

def test_tool_inventory(server) -> None:
    names = set(server.list_tool_names())
    assert names == EXPECTED
    assert not any("delete" in name or "remove" in name for name in names)
```

- [ ] **Step 2: 使用 FastMCP 注册只读工具**

每个工具直接接收 Pydantic 可序列化参数，并返回 `model_dump(mode="json")`。所有异常转换为 `{ok:false,error:{code,message,details}}`，不能把堆栈或请求头返回给 Codex。

- [ ] **Step 3: 注册写工具并要求 confirm**

四个写工具 schema 必须含 `bug_id: int` 和 `confirm: Literal[True]`。工具描述明确说明只有当前用户消息明确要求时才能传 `true`；MCP 内部仍调用 `WriteAuthorization` 二次校验。

- [ ] **Step 4: 实现 stdio 冒烟测试**

启动 `python3 -m zentao_ai.cli mcp serve`，完成 initialize、tools/list，并调用使用假服务的 `query_my_bugs`。子进程 10 秒内未响应即失败，退出后不得遗留进程。

- [ ] **Step 5: 运行 MCP 测试并提交**

```bash
python3 -m pytest tests/contract/test_mcp_tools.py tests/e2e/test_mcp_stdio.py -v
git add src/zentao_ai/server.py tests
git commit -m "feat: expose Zentao MCP tool contract"
```

---

### Task 8: 实现 setup、doctor 与本地配置体验

**Files:**
- Create: `src/zentao_ai/cli.py`
- Create: `tests/e2e/test_cli_setup.py`
- Create: `tests/e2e/test_cli_doctor.py`

**Interfaces:**
- Produces: `zentao-ai setup`、`zentao-ai doctor`、`zentao-ai mcp serve`。

- [ ] **Step 1: 编写 CLI 失败测试**

```python
def test_setup_writes_config_but_not_password(runner, fake_keyring, tmp_path) -> None:
    result = runner.invoke(app, ["setup", "--config", str(tmp_path / "config.yaml")], input=SETUP_INPUT)
    assert result.exit_code == 0
    text = (tmp_path / "config.yaml").read_text()
    assert "secret" not in text
    assert fake_keyring.password == "secret"


def test_doctor_returns_two_when_auth_fails(runner, fake_services) -> None:
    fake_services.auth_error = True
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 2
    assert "AUTH" in result.stdout
    assert "secret" not in result.stdout
```

- [ ] **Step 2: 实现交互式 setup**

依次询问 URL、账号、隐藏密码、团队成员。每个成员可输入账号或姓名；通过 API 解析后展示“姓名 (账号)”确认。已有配置默认拒绝覆盖，只允许 `--update` 合并非秘密字段。

- [ ] **Step 3: 实现 doctor 检查表**

固定检查 `CONFIG`、`CREDENTIALS`、`LOGIN`、`API_V2`、`TEAM_MEMBERS`、`QUERY_MY_BUGS`、`EDIT`、`COMMENT`、`ACTIVATE`、`ASSIGN`、`MCP`。每项输出 PASS/WARN/FAIL；强制项失败返回 2，可选写能力不可用返回 WARN；所有细节经过 `redact`。

- [ ] **Step 4: 接通 mcp serve**

`mcp serve` 加载配置和凭据，构造服务依赖并运行 stdio。标准输出只用于 MCP 协议，诊断日志写标准错误。

- [ ] **Step 5: 运行 CLI 测试并提交**

```bash
python3 -m pytest tests/e2e/test_cli_setup.py tests/e2e/test_cli_doctor.py -v
zentao-ai --help
git add src/zentao_ai/cli.py tests
git commit -m "feat: add three-minute setup and diagnostics"
```

---

### Task 9: 打包 Codex 插件、Skill 与 Marketplace

**Files:**
- Create: `plugins/zentao-ai-bug/.codex-plugin/plugin.json`
- Create: `plugins/zentao-ai-bug/.mcp.json`
- Create: `plugins/zentao-ai-bug/skills/zentao-ai-bug/SKILL.md`
- Create: `.agents/plugins/marketplace.json`
- Create: `tests/contract/test_plugin_package.py`
- Create: `tests/contract/test_skill_behavior.py`

**Interfaces:**
- Produces: 可由 Codex 安装的 `zentao-ai-bug@zentao-ai-assistant` 插件。

- [ ] **Step 1: 编写插件结构失败测试**

```python
def test_manifest_wires_skill_and_mcp(plugin_root: Path) -> None:
    manifest = json.loads((plugin_root / ".codex-plugin/plugin.json").read_text())
    assert manifest["name"] == "zentao-ai-bug"
    assert manifest["version"] == "0.1.0"
    assert manifest["skills"] == "./skills/"
    assert manifest["mcpServers"] == "./.mcp.json"


def test_mcp_uses_installed_cli(plugin_root: Path) -> None:
    config = json.loads((plugin_root / ".mcp.json").read_text())
    server = config["mcpServers"]["zentao"]
    assert server == {"command": "zentao-ai", "args": ["mcp", "serve"], "cwd": "."}
```

- [ ] **Step 2: 用 plugin-creator 生成并验证 manifest**

先运行标准脚手架：

```bash
PLUGIN_CREATOR_ROOT="${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator"
python3 "${PLUGIN_CREATOR_ROOT}/scripts/create_basic_plugin.py" zentao-ai-bug \
  --path plugins \
  --with-skills \
  --with-mcp \
  --with-marketplace \
  --marketplace-path .agents/plugins/marketplace.json \
  --marketplace-name zentao-ai-assistant \
  --install-policy AVAILABLE \
  --auth-policy ON_INSTALL \
  --category Productivity
```

随后把 manifest 改为版本 `0.1.0`、作者 `wwtweiwenting`、仓库 `https://github.com/wwtweiwenting/zentao-ai-assistant`、许可证 `Apache-2.0`、中文显示名“禅道 AI Bug 助手”、开发者名 `wwtweiwenting`、Productivity 分类、简短/详细描述和不超过三条默认提示；不引用不存在的图标、App 或 hooks。Marketplace 名称固定 `zentao-ai-assistant`，策略为 `AVAILABLE` 与 `ON_INSTALL`。

- [ ] **Step 3: 编写 Skill**

Skill 明确：

- “我/自己”调用 `query_my_bugs`；
- “团队”调用配置团队的 `query_team_bugs`；
- 具体姓名/账号调用 `query_user_bugs`，不要求在团队中；
- 组合条件调用 `search_bugs`；
- 列表统一输出数量、分布和表格；
- 写操作必须绑定当前消息的 Bug ID、动作和完整参数，并设置 `confirm:true`；
- 模糊目标先询问，删除永久拒绝。

- [ ] **Step 4: 运行插件和 Skill 合同**

```bash
PLUGIN_CREATOR_ROOT="${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator"
python3 "${PLUGIN_CREATOR_ROOT}/scripts/validate_plugin.py" plugins/zentao-ai-bug
python3 -m pytest tests/contract/test_plugin_package.py tests/contract/test_skill_behavior.py -v
```

预期：manifest、Marketplace、MCP 和 Skill 全部通过，删除工具不存在。

- [ ] **Step 5: 提交插件包**

```bash
git add plugins .agents/plugins/marketplace.json tests/contract
git commit -m "feat: package Zentao Codex plugin"
```

---

### Task 10: 实现 macOS/Linux 与 Windows 幂等安装器

**Files:**
- Create: `scripts/install.sh`
- Create: `scripts/install.ps1`
- Create: `tests/e2e/test_install_scripts.py`

**Interfaces:**
- Consumes: Python 3.11+、Codex CLI、仓库根目录。
- Produces: 已安装 `zentao-ai` 命令、已注册 Marketplace、已安装插件和可选启动的 setup。

- [ ] **Step 1: 编写静态和隔离环境安装测试**

测试断言两个脚本都：检查 Python 版本、检查 `codex`、使用 pipx 隔离安装、注册当前仓库 Marketplace、安装 `zentao-ai-bug@zentao-ai-assistant`、运行 doctor、支持 `--non-interactive`、不输出密码。

- [ ] **Step 2: 实现 POSIX 安装器**

`install.sh` 使用 `set -eu`，解析真实仓库根路径。没有 pipx 时运行 `python3 -m pip install --user pipx` 和 `python3 -m pipx ensurepath`；随后：

```sh
python3 -m pipx install --force "${repo_root}"
codex plugin marketplace add "${repo_root}"
codex plugin add zentao-ai-bug@zentao-ai-assistant
```

已存在 Marketplace 或插件时使用可重复的升级/重装分支，不把预期的“已存在”当成失败。

- [ ] **Step 3: 实现 PowerShell 安装器**

`install.ps1` 使用 `$ErrorActionPreference = 'Stop'`，选择 `py -3.11` 或 `python`，用 `& $python -m pipx` 执行同一安装逻辑。所有路径使用 `Resolve-Path` 和参数数组，禁止拼接执行用户输入。

- [ ] **Step 4: 验证三分钟路径**

在临时用户目录和伪造 `codex` 命令下执行两套脚本，断言命令顺序、第二次运行成功、已有配置保持字节不变。真实 macOS 计时从脚本开始到 doctor 完成，不计依赖下载和用户输入。

- [ ] **Step 5: 运行测试并提交**

```bash
python3 -m pytest tests/e2e/test_install_scripts.py -v
shellcheck scripts/install.sh
git add scripts tests/e2e/test_install_scripts.py
git commit -m "feat: add cross-platform plugin installers"
```

---

### Task 11: 补齐 GitHub 首屏和详细使用文档

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `SECURITY.md`
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`
- Create: `docs/installation.md`
- Create: `docs/configuration.md`
- Create: `docs/features.md`
- Create: `docs/security.md`
- Create: `docs/troubleshooting.md`
- Create: `tests/contract/test_documentation.py`

**Interfaces:**
- Produces: 与实际命令和配置一致的三分钟使用说明。

- [ ] **Step 1: 编写文档合同测试**

```python
def test_readme_has_three_minute_path(readme: str) -> None:
    required = ["21.7.8", "scripts/install.sh", "scripts/install.ps1", "zentao-ai setup", "zentao-ai doctor"]
    assert all(item in readme for item in required)


def test_docs_never_show_plaintext_secrets(all_docs: str) -> None:
    assert "password: 123" not in all_docs
    assert "token: " not in all_docs.lower()
```

- [ ] **Step 2: 编写 README 三分钟快速开始**

README 首屏顺序固定为：功能摘要、兼容版本、前置条件、Git clone、两平台安装命令、配置文件位置、五条自然语言示例、写入安全、详细文档链接。明确当前仓库安装完成后需要重启 Codex 或新建任务。

- [ ] **Step 3: 编写配置和功能文档**

`configuration.md` 逐字段解释 URL、账号、团队、默认状态、分页和写开关；密码只通过 setup/keyring。`features.md` 用矩阵列出个人、团队、外部用户、组合过滤、详情、备注、编辑、激活和指派，并明确不支持创建/解决/关闭/删除。

- [ ] **Step 4: 编写安全和排错文档**

说明 Token 401 重登、写超时 UNKNOWN、当前轮次授权、TLS、权限要求和秘密报告流程。排错按 doctor 的固定检查项给出原因与修复命令。

- [ ] **Step 5: 添加开源治理并验证**

许可证采用 Apache-2.0；SECURITY.md 要求使用 GitHub Security Advisory，不在 Issue 中发送凭据或业务 Bug。运行：

```bash
python3 -m pytest tests/contract/test_documentation.py tests/contract/test_repository_hygiene.py -v
git add README.md LICENSE SECURITY.md CONTRIBUTING.md CHANGELOG.md docs tests/contract
git commit -m "docs: add three-minute Zentao plugin guide"
```

---

### Task 12: CI、全量验收、GitHub 推送与安装复核

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `docs/release-checklist.md`
- Create: `docs/acceptance/zentao-21.7.8.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: 可审计的 CI、脱敏验收记录和远端分支。

- [ ] **Step 1: 添加三平台 CI**

GitHub Actions 矩阵使用 `ubuntu-latest`、`macos-latest`、`windows-latest` 与 Python 3.11/3.12/3.13。每个作业运行 pytest、Ruff、mypy、build、twine check、插件 validator 和仓库秘密合同；Windows 安装器测试只在 Windows，shellcheck 只在 Ubuntu。

- [ ] **Step 2: 运行本地完整验证**

```bash
python3 -m pytest -v
python3 -m ruff check src tests
python3 -m mypy src
python3 -m build
python3 -m twine check dist/*
PLUGIN_CREATOR_ROOT="${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator"
python3 "${PLUGIN_CREATOR_ROOT}/scripts/validate_plugin.py" plugins/zentao-ai-bug
git diff --check
```

预期：全部通过且退出码为 0。

- [ ] **Step 3: 运行秘密与历史扫描**

```bash
git grep -nEi '(password|token|cookie)[[:space:]]*[:=][[:space:]]*[^$<{]' -- ':!docs/superpowers/**'
git log -p --all -- . ':!docs/superpowers/**' | grep -Ei '(password|token|cookie)[[:space:]]*[:=]' || true
git status --short
```

逐项审核命中，只允许示例占位或环境变量引用；真实域名、账号、成员、Token、密码和业务数据必须为零。

- [ ] **Step 4: 在真实 21.7.8 测试实例验收**

使用 `zentao-ai setup` 写入本机凭据，运行 `doctor`，然后依次验证：个人未关闭列表、团队汇总、团队外用户、组合过滤、Bug 详情、备注、编辑、激活、指派、过期 Token 重登。验收文档只记录日期、版本、测试类别与 PASS/FAIL，不记录真实 ID、姓名或响应内容。

- [ ] **Step 5: 从当前仓库执行干净安装复核**

在临时用户环境重新 clone 当前分支，运行平台安装器、新建 Codex 任务并执行五条 README 示例。计时不超过三分钟，不计网络下载和手工输入；任何 README 与真实步骤差异必须先修正文档或安装器。

- [ ] **Step 6: 提交发布材料并推送**

```bash
git add .github docs/release-checklist.md docs/acceptance/zentao-21.7.8.md CHANGELOG.md
git commit -m "ci: verify Zentao plugin across platforms"
git push -u origin codex/zentao-plugin-v0.1
```

预期：远端分支存在，CI 启动；返回分支链接、实际安装命令、测试摘要和真实实例验收中仍需用户完成的项目。

---

## 最终验收清单

- [ ] GitHub 仓库保留原提交历史，所有新增提交位于 `codex/zentao-plugin-v0.1`。
- [ ] 从 clone 到 doctor 全绿的实际步骤与 README 完全一致。
- [ ] 个人、团队、外部人员和组合条件查询均通过 MCP 与 Codex 端到端测试。
- [ ] 备注、编辑、激活和指派都要求当前轮次明确授权并验证前后快照。
- [ ] Token 401 后只重新登录和重放一次；写超时不自动重试。
- [ ] MCP、Skill、CLI 和 Python 服务均不存在删除 Bug 能力。
- [ ] 配置、凭据、日志、异常、文档、提交和构建产物中没有真实秘密或业务数据。
- [ ] macOS/Linux 与 Windows 安装脚本可重复执行且不覆盖配置。
- [ ] pytest、Ruff、mypy、build、twine、插件验证、文档合同和秘密扫描全部通过。
- [ ] 远端分支已推送，CI 结果可查看，安装与使用说明可在三分钟内完成。

