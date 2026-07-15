import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render-report.py"
FIXTURES = Path(__file__).parent / "fixtures"


def render(mode: str, fixture: str) -> subprocess.CompletedProcess[str]:
    payload = (FIXTURES / fixture).read_text(encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--mode", mode],
        input=payload,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


class ReportRendererTests(unittest.TestCase):
    def test_personal_report_uses_approved_groups_and_truthful_results(self):
        result = render("personal", "personal-report.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout
        self.assertIn("# 个人 Bug 日报", text)
        self.assertIn("## 等待补充信息 Bug", text)
        self.assertIn("## 人工需走查 Bug", text)
        self.assertNotIn("AI已分析 Bug", text)
        self.assertNotIn("未处理 Bug", text)
        self.assertEqual(text.count("BUG-1001｜"), 1)
        self.assertEqual(text.count("BUG-1002｜"), 1)
        self.assertIn("AI评论：FAILED / None", text)
        self.assertIn("拟添加备注（写入失败）：", text)
        self.assertNotIn("AI已在禅道上添加备注", text)
        self.assertIn("未声称修复完成", text)
        self.assertIn("覆盖范围：example-web、example-api、example-ai-web、example-ai-api", text)

    def test_team_report_keeps_candidates_and_renders_totals_table(self):
        result = render("team", "team-report.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout
        self.assertIn("# 团队 Bug 汇总", text)
        self.assertIn("覆盖成员：4 人", text)
        self.assertIn("| Example Member A | 1 | 0 | 0 |", text)
        self.assertIn("| 合计 | 3 | 0 | 0 |", text)
        self.assertIn("BUG-1003：Synthetic editor field example，负责人Example Member A，active，P3", text)
        self.assertIn("完整性：部分完成。", text)
        self.assertIn("写操作：未执行", text)

    def test_personal_report_rejects_duplicate_bug_groups(self):
        data = json.loads((FIXTURES / "personal-report.json").read_text(encoding="utf-8"))
        data["walkthroughBugs"].append(data["informationBugs"][0])
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--mode", "personal"],
            input=json.dumps(data, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate Bug", result.stderr)


if __name__ == "__main__":
    unittest.main()
