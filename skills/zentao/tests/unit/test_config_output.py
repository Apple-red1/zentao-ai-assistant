
from __future__ import annotations

import contextlib
import io
import os
import stat
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch

from ..support import SCRIPTS
from zentao_skill.cli.main import _run_setup
from zentao_skill.cli.output import emit_error, emit_success
from zentao_skill.internal.config import encode_env_value, load_config, parse_env, project_root, write_private_text_atomic
from zentao_skill.internal.zentao.common import make_order_by, map_enum, validate_pagination
from zentao_skill.internal.errors import ApiError, ConfigError, UsageError


class UnitTests(unittest.TestCase):
    def test_minimal_env_parser(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/".env"
            path.write_text('A=one\nB="two words"\nC=\'three\'\nD="pa\\"ss\\\\word  "\n# comment\n',encoding="utf-8")
            self.assertEqual({"A":"one","B":"two words","C":"three","D":"pa\"ss\\word  "}, parse_env(path))

    def test_setup_and_load_config_round_trip_secret_without_logging_it(self) -> None:
        passwords = [
            'pa"ss\\word',
            "中文#密码=part",
            "  leading-and-trailing  ",
        ]
        for password in passwords:
            with self.subTest(password_shape=len(password)), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                args = Namespace(base_url="https://zentao.example.com/", account="admin")
                with patch("zentao_skill.cli.main.project_root", return_value=root), patch("zentao_skill.cli.main.getpass.getpass", return_value=password):
                    result = _run_setup(None, args)
                self.assertEqual({"status": "success", "path": str(root / ".env")}, result)
                with patch("zentao_skill.internal.config.project_root", return_value=root), patch.dict(os.environ, {}, clear=True):
                    config = load_config()
                self.assertEqual("https://zentao.example.com", config.base_url)
                self.assertEqual("admin", config.account)
                self.assertEqual(password, config.password)

    def test_dotenv_codec_rejects_values_it_cannot_round_trip(self) -> None:
        for value in ("line\nbreak", "carriage\rreturn", "nul\x00byte"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ConfigError):
                    encode_env_value(value)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".env"
            path.write_text('PASSWORD="bad\\q"\n', encoding="utf-8")
            with self.assertRaises(ConfigError):
                parse_env(path)

    def test_setup_creates_private_file_even_with_permissive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            previous = os.umask(0)
            try:
                with patch("zentao_skill.cli.main.project_root", return_value=root), patch("zentao_skill.cli.main.getpass.getpass", return_value="safe-secret"):
                    _run_setup(None, Namespace(base_url="https://zentao.example.com", account="admin"))
            finally:
                os.umask(previous)
            if os.name == "posix":
                self.assertEqual(0o600, stat.S_IMODE((root / ".env").stat().st_mode))
            self.assertFalse(list(root.glob(".env.*")))

    def test_atomic_write_failure_preserves_old_file_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / ".env"
            target.write_text("old-config\n", encoding="utf-8")
            with patch("zentao_skill.internal.config.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaises(ConfigError) as error:
                    write_private_text_atomic(target, "new-secret\n")
            self.assertNotIn("new-secret", str(error.exception))
            self.assertEqual("old-config\n", target.read_text(encoding="utf-8"))
            self.assertFalse(list(Path(td).glob(".env.*")))

    def test_fsync_failure_is_reported_without_destroying_old_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / ".env"
            target.write_text("old-config\n", encoding="utf-8")
            with patch("zentao_skill.internal.config.os.fsync", side_effect=OSError("fsync failed")):
                with self.assertRaises(ConfigError):
                    write_private_text_atomic(target, "new-secret\n")
            self.assertEqual("old-config\n", target.read_text(encoding="utf-8"))
            self.assertFalse(list(Path(td).glob(".env.*")))

    def test_enum_and_sort_mapping(self) -> None:
        self.assertEqual("assignedtome", map_enum("browseType","assigned-to-me"))
        self.assertEqual("rawID_desc", make_order_by("raw-id","desc"))

    def test_pagination_validation(self) -> None:
        validate_pagination(1,1000)
        with self.assertRaises(UsageError): validate_pagination(0,10)
        with self.assertRaises(UsageError): validate_pagination(1,1001)


    def test_project_root_does_not_depend_on_current_working_directory(self) -> None:
        original=Path.cwd()
        with tempfile.TemporaryDirectory() as td:
            try:
                os.chdir(td)
                self.assertEqual(Path(__file__).resolve().parents[4], project_root())
            finally:
                os.chdir(original)

    def test_error_output_redacts_nested_password_and_token_keys(self) -> None:
        err=io.StringIO()
        exc=ApiError("failed", {"ZENTAO_PASSWORD":"secret","response":{"resetToken":"abc","Authorization":"Bearer xyz"}})
        with contextlib.redirect_stderr(err): emit_error(exc,json_output=True)
        text=err.getvalue()
        self.assertNotIn("secret",text); self.assertNotIn("abc",text); self.assertNotIn("xyz",text)
        self.assertGreaterEqual(text.count('"***"'),3)

    def test_output_redacts_secrets(self) -> None:
        out=io.StringIO()
        with contextlib.redirect_stdout(out): emit_success({"token":"abc","password":"secret","id":1},json_output=True)
        text=out.getvalue()
        self.assertNotIn("abc",text); self.assertNotIn("secret",text)
        self.assertIn('"token":"***"',text)


if __name__ == "__main__": unittest.main()
