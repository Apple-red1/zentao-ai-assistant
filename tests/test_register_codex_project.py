import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "register-codex-project.ps1"
PROJECT = "${PROJECT_ROOT}"


class RegisterCodexProjectTests(unittest.TestCase):
    def test_prepends_project_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            original = {
                "electron-saved-workspace-roots": [
                    "F:\\vcp",
                    "${OTHER_PROJECT_B}",
                ],
                "project-order": [
                    "F:\\vcp",
                    "${OTHER_PROJECT_B}",
                ],
                "unrelated-setting": {"keep": True},
            }
            state_path.write_text(
                json.dumps(original, ensure_ascii=False), encoding="utf-8"
            )

            command = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                "-StatePath",
                str(state_path),
                "-ProjectPath",
                PROJECT,
            ]
            for _ in range(2):
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

            updated = json.loads(state_path.read_text(encoding="utf-8-sig"))
            for key in ("electron-saved-workspace-roots", "project-order"):
                self.assertEqual(updated[key][0], PROJECT)
                self.assertEqual(updated[key].count(PROJECT), 1)
                self.assertEqual(updated[key][1:], original[key])
            self.assertEqual(updated["unrelated-setting"], {"keep": True})


if __name__ == "__main__":
    unittest.main()
