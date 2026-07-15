import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "tests" / "fixtures" / "config" / "valid.yaml"


def validate(path: Path) -> tuple[int, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = [
        {"field": f"{section}.scopeNames"}
        for section in ("personal", "team")
        if not data.get(section, {}).get("scopeNames")
    ]
    return (1 if errors else 0), {
        "valid": not errors,
        "redactedConfig": data,
        "errors": errors,
    }


class ConfigContractTests(unittest.TestCase):
    def test_daily_work_config_has_distinct_personal_and_team_scopes(self):
        code, result = validate(CONFIG)
        self.assertEqual(code, 0, result)
        self.assertTrue(result["valid"])
        config = result["redactedConfig"]
        self.assertEqual(config["personal"]["scopeNames"], [
            "example-web", "example-api", "example-ai-web", "example-ai-api",
        ])
        self.assertEqual(config["team"]["scopeNames"], [
            "example-web", "example-ai-web", "example-lowcode",
        ])

    def test_validator_rejects_missing_mode_specific_scopes(self):
        for section in ("personal", "team"):
            with self.subTest(section=section):
                data = json.loads(CONFIG.read_text(encoding="utf-8"))
                del data[section]["scopeNames"]
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "invalid.yaml"
                    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                    code, result = validate(path)
                self.assertNotEqual(code, 0)
                self.assertFalse(result["valid"])
                self.assertIn(
                    f"{section}.scopeNames",
                    {error["field"] for error in result["errors"]},
                )


if __name__ == "__main__":
    unittest.main()
