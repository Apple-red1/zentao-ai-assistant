# GitHub-only Codex 插件交付设计

## 目标

团队成员无需预先 clone 仓库，也无需引用任何本地 Marketplace 路径。Codex 插件 Marketplace 和配套 CLI 均直接从 GitHub 仓库的 `feature/zentao-open-source` 分支获取。

## 安装入口

CLI 使用 Git VCS URL 安装：

```powershell
pipx install "git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source"
```

Codex Marketplace 使用 GitHub 仓库坐标注册：

```powershell
codex plugin marketplace add "wwtweiwenting/zentao-ai-assistant@feature/zentao-open-source"
```

Marketplace 内部的 `source.local.path` 继续使用 `./plugins/zentao-ai-bug`。这是 Marketplace 仓库内部定位插件目录的规范格式，不是用户电脑上的本地安装入口。

## 文档与测试

- 安装文档以 GitHub 命令为默认且唯一面向团队成员的安装流程。
- 不再要求执行 `git clone`、`pipx install .` 或 `codex plugin marketplace add .`。
- 合同测试必须验证 GitHub 仓库、分支和两条安装命令，禁止本地安装命令重新进入交付文档。
- 使用临时 `CODEX_HOME` 验证 GitHub Marketplace 注册，不修改用户现有 Codex 配置。

## 私有仓库约束

仓库保持私有时，团队成员必须先在 GitHub CLI 或 Git 凭据管理器中登录并拥有仓库读取权限。仓库公开后，两条安装命令保持不变。

## 验收标准

1. 团队安装文档只提供 GitHub 来源命令。
2. 官方 Plugin 与 Skill validators 通过。
3. Plugin contracts、Ruff 和相关测试通过。
4. 临时 Codex 配置能够识别 GitHub Marketplace 来源。
5. 变更推送至 `origin/feature/zentao-open-source`。
