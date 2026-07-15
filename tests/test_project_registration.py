import json
import unittest
from pathlib import Path


FIXTURES = Path(__file__).parent / "fixtures"
PROJECT = "${PROJECT_ROOT}"
STATE = FIXTURES / "project-registration" / "global-state.json"


class ProjectRegistrationTests(unittest.TestCase):
    def test_daily_work_is_first_registered_project(self):
        state = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(state["electron-saved-workspace-roots"][0], PROJECT)
        self.assertEqual(state["project-order"][0], PROJECT)

    def test_config_lives_only_in_daily_work_project(self):
        registered = json.loads(STATE.read_text(encoding="utf-8"))["config-paths"]
        self.assertEqual(registered, ["${PROJECT_ROOT}/tests/fixtures/config/valid.yaml"])


if __name__ == "__main__":
    unittest.main()
