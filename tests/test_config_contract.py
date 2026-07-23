import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from zentao_ai.config import validate_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "tests" / "fixtures" / "config" / "valid.yaml"


class ConfigContractTests(unittest.TestCase):
    def test_daily_work_config_has_distinct_personal_and_team_scopes(self):
        result = validate_config(CONFIG)
        self.assertTrue(result.valid, result.errors)
        config = result.redactedConfig
        assert config is not None
        self.assertEqual(config["personal"]["scopeNames"], [
            "example-web", "example-api", "example-ai-web", "example-ai-api",
        ])
        self.assertEqual(config["team"]["scopeNames"], [
            "example-web", "example-ai-web", "example-lowcode",
        ])

    def test_validator_rejects_missing_mode_specific_scopes(self):
        for section in ("personal", "team"):
            with self.subTest(section=section):
                data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
                del data[section]["scopeNames"]
                with TemporaryDirectory() as directory:
                    path = Path(directory) / "invalid.yaml"
                    path.write_text(yaml.safe_dump(data), encoding="utf-8")
                    result = validate_config(path)
                self.assertFalse(result.valid)
                self.assertIn(
                    f"{section}.scopeNames",
                    {error.field for error in result.errors},
                )


if __name__ == "__main__":
    unittest.main()
