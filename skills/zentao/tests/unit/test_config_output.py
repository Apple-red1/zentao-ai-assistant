
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from ..support import SCRIPTS
from zentao_skill.cli.output import emit_error, emit_success
from zentao_skill.internal.config import parse_env, project_root
from zentao_skill.internal.zentao.common import make_order_by, map_enum, validate_pagination
from zentao_skill.internal.errors import ApiError, UsageError


class UnitTests(unittest.TestCase):
    def test_minimal_env_parser(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/".env"
            path.write_text("A=one\nB=\"two words\"\nC='three'\n# comment\n",encoding="utf-8")
            self.assertEqual({"A":"one","B":"two words","C":"three"}, parse_env(path))

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
