import unittest
from pathlib import Path
import tomllib


AUTOMATIONS = Path(__file__).parent / "fixtures" / "automations"


class AutomationContractTests(unittest.TestCase):
    def assert_common(self, text: str) -> None:
        self.assertIn('rrule = "FREQ=DAILY;BYHOUR=8;BYMINUTE=0"', text)
        self.assertIn('project_id = "${PROJECT_ROOT}"', text)
        self.assertIn('cwds = ["${PROJECT_ROOT}"]', text)
        self.assertIn('${PROJECT_ROOT}/tests/fixtures/config/valid.yaml', text)

    def test_personal_automation_uses_daily_work_and_v2_personal_renderer(self):
        path = AUTOMATIONS / "bug-ai" / "automation.toml"
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
        self.assert_common(text)
        self.assertEqual(data["target"]["project_id"], "${PROJECT_ROOT}")
        self.assertEqual(data["cwds"], ["${PROJECT_ROOT}"])
        self.assertIn("personal.scopeNames", text)
        self.assertIn("--mode personal", text)
        self.assertIn("默认执行模式", text)

    def test_team_automation_uses_daily_work_and_stays_read_only(self):
        path = AUTOMATIONS / "bug" / "automation.toml"
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
        self.assert_common(text)
        self.assertEqual(data["target"]["project_id"], "${PROJECT_ROOT}")
        self.assertEqual(data["cwds"], ["${PROJECT_ROOT}"])
        self.assertIn("team.scopeNames", text)
        self.assertIn("--mode team", text)
        self.assertIn("严格只读", text)


if __name__ == "__main__":
    unittest.main()
