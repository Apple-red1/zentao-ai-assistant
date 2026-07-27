from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_has_three_minute_path() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    required = (
        "21.7.8",
        "git clone",
        "scripts/install.sh",
        "scripts/install.ps1",
        "zentao-ai setup",
        "zentao-ai doctor",
        "~/.codex/zentao-ai-bug/config.yaml",
        "新建任务",
    )

    assert all(item in readme for item in required)


def test_documentation_links_point_to_existing_files() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]+\]\((docs/[^)#]+\.md)\)", readme)

    assert links
    assert all((ROOT / link).is_file() for link in links)


def test_docs_cover_configuration_features_security_and_troubleshooting() -> None:
    configuration = (ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    features = (ROOT / "docs" / "features.md").read_text(encoding="utf-8")
    security = (ROOT / "docs" / "security.md").read_text(encoding="utf-8")
    troubleshooting = (ROOT / "docs" / "troubleshooting.md").read_text(encoding="utf-8")

    for key in ("base_url", "account", "members", "default_status", "page_size", "writes"):
        assert key in configuration
    for feature in ("个人", "团队", "外部人员", "组合条件", "备注", "编辑", "激活", "指派"):
        assert feature in features
    assert "401" in security and "UNKNOWN_WRITE_RESULT" in security
    assert all(name in troubleshooting for name in ("CONFIG", "LOGIN", "QUERY_MY_BUGS", "MCP"))


def test_docs_do_not_teach_plaintext_secret_configuration() -> None:
    files = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
    text = "\n".join(path.read_text(encoding="utf-8") for path in files)

    assert "password: 123" not in text.casefold()
    assert "token: " not in text.casefold()
    assert "把密码写入 yaml" not in text
