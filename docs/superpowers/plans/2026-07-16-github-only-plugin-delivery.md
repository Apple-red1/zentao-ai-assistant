# GitHub-only Plugin Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Zentao CLI and Codex Marketplace installable directly from the GitHub feature branch without clone-based or local-path user instructions.

**Architecture:** Keep the repository Marketplace layout and its required relative plugin source unchanged. Replace only the consumer-facing delivery entrypoints with GitHub VCS/repository coordinates, then enforce them with contract tests and verify registration in an isolated Codex home.

**Tech Stack:** Markdown, JSON Marketplace metadata, Python 3.12, pytest, Codex CLI 0.130.0, pipx, GitHub.

## Global Constraints

- GitHub repository: `wwtweiwenting/zentao-ai-assistant`.
- Delivery branch: `feature/zentao-open-source`.
- CLI source: `git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source`.
- Marketplace source: `wwtweiwenting/zentao-ai-assistant@feature/zentao-open-source`.
- Preserve `.agents/plugins/marketplace.json` entry path `./plugins/zentao-ai-bug`.
- Never modify the user's real Codex configuration during automated verification.

---

### Task 1: Enforce GitHub-only installation documentation

**Files:**
- Modify: `tests/contract/test_plugin_package.py`
- Modify: `docs/plugin-installation.md`

**Interfaces:**
- Consumes: repository and branch constants from the approved design.
- Produces: a documented two-command GitHub installation contract.

- [ ] **Step 1: Write the failing contract assertions**

Update `test_installation_document_covers_supported_plugin_flow` to require these exact strings:

```python
github_cli = (
    'pipx install "git+https://github.com/wwtweiwenting/'
    'zentao-ai-assistant.git@feature/zentao-open-source"'
)
github_marketplace = (
    'codex plugin marketplace add '
    '"wwtweiwenting/zentao-ai-assistant@feature/zentao-open-source"'
)
assert github_cli in text
assert github_marketplace in text
assert "pipx install ." not in text
assert "codex plugin marketplace add ." not in text
```

- [ ] **Step 2: Run the contract and verify RED**

Run:

```powershell
python -m pytest tests/contract/test_plugin_package.py::test_installation_document_covers_supported_plugin_flow -q
```

Expected: FAIL because the document still presents local commands.

- [ ] **Step 3: Replace the installation instructions**

Make `docs/plugin-installation.md` present these commands as the primary flow:

```powershell
pipx install "git+https://github.com/wwtweiwenting/zentao-ai-assistant.git@feature/zentao-open-source"
codex plugin marketplace add "wwtweiwenting/zentao-ai-assistant@feature/zentao-open-source"
```

Explain that private-repository users need GitHub read access and authenticated Git credentials. Keep the Codex app enablement, credential isolation, and safety guidance unchanged.

- [ ] **Step 4: Run the contract and verify GREEN**

Run the Step 2 command.

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```powershell
git add docs/plugin-installation.md tests/contract/test_plugin_package.py
git commit -m "docs: install plugin directly from GitHub"
```

### Task 2: Validate remote Marketplace delivery

**Files:**
- Modify: `tests/contract/test_plugin_package.py`
- Create: `.superpowers/sdd/github-delivery-report.md` (ignored verification evidence)

**Interfaces:**
- Consumes: GitHub Marketplace coordinate from Task 1.
- Produces: repeatable evidence that Codex resolves the repository Marketplace without local configuration changes.

- [ ] **Step 1: Add repository-coordinate contract coverage**

Add a test which asserts the install document contains the repository coordinate and the Marketplace retains the internal relative path:

```python
def test_github_marketplace_keeps_repository_relative_plugin_path() -> None:
    text = (ROOT / "docs" / "plugin-installation.md").read_text(encoding="utf-8")
    assert "wwtweiwenting/zentao-ai-assistant@feature/zentao-open-source" in text
    market = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    entry = next(item for item in market["plugins"] if item["name"] == "zentao-ai-bug")
    assert entry["source"] == {"source": "local", "path": "./plugins/zentao-ai-bug"}
```

- [ ] **Step 2: Run plugin contracts**

```powershell
python -m pytest tests/contract/test_plugin_package.py -q
```

Expected: all plugin contracts pass.

- [ ] **Step 3: Push the documentation commit before remote resolution**

```powershell
git push origin feature/zentao-open-source
```

Expected: remote feature branch advances to the local commit.

- [ ] **Step 4: Register the GitHub Marketplace in an isolated Codex home**

Create a temporary directory, set `CODEX_HOME` only for the child command, and run:

```powershell
codex plugin marketplace add "wwtweiwenting/zentao-ai-assistant@feature/zentao-open-source"
```

Expected: exit code 0 and Marketplace name `zentao-team`. Remove only the verified temporary directory afterward and confirm the SHA-256 of the real `~/.codex/config.toml` is unchanged.

- [ ] **Step 5: Run official validators and static checks**

```powershell
python C:\Users\wwtlove66\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\zentao-ai-bug
python C:\Users\wwtlove66\.codex\skills\.system\skill-creator\scripts\quick_validate.py plugins\zentao-ai-bug\skills\zentao-ai-bug
python -m ruff check .
```

Expected: all commands pass.

- [ ] **Step 6: Record evidence and commit the test**

Record exact commands, exit codes, resolved Marketplace name, and real-config before/after hashes in `.superpowers/sdd/github-delivery-report.md`, then commit the tracked test:

```powershell
git add tests/contract/test_plugin_package.py
git commit -m "test: verify GitHub Marketplace delivery"
git push origin feature/zentao-open-source
```

Expected: local and remote branch heads match.
