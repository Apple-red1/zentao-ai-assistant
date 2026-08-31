from __future__ import annotations

import unittest

from zentao_skill.internal.http.legacy_bug import parse_form
from zentao_skill.internal.zentao.bug_steps import hidden_value


class BugFormUidTests(unittest.TestCase):
    def test_text_uid_is_available_to_steps_flow(self) -> None:
        form = parse_form(
            b'<form action="/index.php?m=bug&amp;f=create&amp;productID=1">'
            b'<input type="text" name="uid" value="text-uid">'
            b'<input type="text" name="title" value="must-not-be-collected">'
            b'<input type="hidden" name="csrf" value="csrf-value">'
            b'</form>'
        )

        self.assertIsNotNone(form)
        self.assertEqual("text-uid", hidden_value(form, "uid"))
        self.assertEqual((("csrf", "csrf-value"),), form.hidden_fields)

    def test_hidden_uid_remains_available_to_steps_flow(self) -> None:
        form = parse_form(
            b'<form action="/index.php?m=bug&amp;f=create&amp;productID=1">'
            b'<input type="hidden" name="uid" value="hidden-uid">'
            b'</form>'
        )

        self.assertIsNotNone(form)
        self.assertEqual("hidden-uid", hidden_value(form, "uid"))

    def test_empty_uid_fails_closed(self) -> None:
        form = parse_form(
            b'<form action="/index.php?m=bug&amp;f=create&amp;productID=1">'
            b'<input type="text" name="uid" value="   ">'
            b'</form>'
        )

        self.assertIsNotNone(form)
        self.assertIsNone(hidden_value(form, "uid"))

    def test_conflicting_uid_controls_fail_closed(self) -> None:
        form = parse_form(
            b'<form action="/index.php?m=bug&amp;f=create&amp;productID=1">'
            b'<input type="hidden" name="uid" value="hidden-uid">'
            b'<input type="text" name="uid" value="text-uid">'
            b'</form>'
        )

        self.assertIsNotNone(form)
        self.assertIsNone(hidden_value(form, "uid"))

    def test_non_uid_text_controls_are_not_collected(self) -> None:
        form = parse_form(
            b'<form action="/index.php?m=bug&amp;f=create&amp;productID=1">'
            b'<input type="text" name="title" value="title">'
            b'</form>'
        )

        self.assertIsNotNone(form)
        self.assertEqual((), form.hidden_fields)
        self.assertIsNone(hidden_value(form, "uid"))

    def test_unsupported_uid_control_type_fails_closed(self) -> None:
        form = parse_form(
            b'<form action="/index.php?m=bug&amp;f=create&amp;productID=1">'
            b'<input type="password" name="uid" value="not-allowed">'
            b'</form>'
        )

        self.assertIsNotNone(form)
        self.assertIsNone(hidden_value(form, "uid"))


if __name__ == "__main__":
    unittest.main()
