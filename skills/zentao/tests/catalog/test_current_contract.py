from __future__ import annotations

import unittest
from pathlib import Path

from ..support import SKILL_ROOT


REPO_ROOT = SKILL_ROOT.parents[1]
CURRENT = REPO_ROOT / "docs" / "current-contract.md"
HISTORICAL = SKILL_ROOT / "RULES.md"


class CurrentContractDocumentationTest(unittest.TestCase):
    def test_current_contract_is_the_only_current_authority_marker(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        historical = HISTORICAL.read_text(encoding="utf-8")
        self.assertIn("CURRENT / 当前唯一权威入口", current)
        self.assertIn("ARCHIVED / 已归档", historical)
        self.assertIn("docs/current-contract.md", historical)
        self.assertNotIn("当前权威规则", historical)

        marked = []
        for path in REPO_ROOT.rglob("*.md"):
            if path == HISTORICAL:
                continue
            if "当前权威规则" in path.read_text(encoding="utf-8"):
                marked.append(path.relative_to(REPO_ROOT).as_posix())
        self.assertEqual([], marked)

    def test_current_contract_describes_implemented_capabilities(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        for required in (
            "120 个 ZenTao API v2 endpoint",
            "R3 delete",
            "--yes",
            "python3 skills/zentao/tests/run_all.py",
            "Real API calls: 0",
            "official-contract.json",
            "zentao-21.7.8.json",
        ):
            self.assertIn(required, current)
        for stale in ("当前仓库仍存在旧形态", "不暴露 Bug 删除命令", "本轮明确延期"):
            self.assertNotIn(stale, current)


if __name__ == "__main__":
    unittest.main()
