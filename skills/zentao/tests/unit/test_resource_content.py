from __future__ import annotations

import unittest

from zentao_skill.services.resources.service import _looks_like_html


class ResourceContentSniffingTests(unittest.TestCase):
    def test_binary_image_sample_that_contains_html_like_bytes_is_not_html(self) -> None:
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00"
            b"<p\x1cIDATx\x9c\x00\x00\x01"
        )
        self.assertFalse(_looks_like_html(png))

    def test_text_with_control_character_after_tag_name_is_not_html(self) -> None:
        for control in range(0x1C, 0x20):
            with self.subTest(control=control):
                self.assertFalse(_looks_like_html(b"before<p" + bytes([control]) + b"after"))

    def test_plain_text_html_is_still_html(self) -> None:
        self.assertTrue(_looks_like_html(b"<!DOCTYPE html><html><body>login</body></html>"))

    def test_text_html_with_ascii_whitespace_is_still_html(self) -> None:
        for whitespace in b" \t\r\n\f\v":
            with self.subTest(whitespace=whitespace):
                self.assertTrue(_looks_like_html(b"<div" + bytes([whitespace]) + b'class="x">hello</div>'))

    def test_non_utf8_html_is_still_html(self) -> None:
        self.assertTrue(_looks_like_html("<!DOCTYPE html><html><body>请登录</body></html>".encode("gbk")))

    def test_html_with_invalid_utf8_is_still_html(self) -> None:
        for sample in (
            b"\xff<html><body>login</body></html>",
            b"<html><body>login\xff</body></html>",
            b"<html><body>login</body></html>\xff",
        ):
            with self.subTest(sample=sample):
                self.assertTrue(_looks_like_html(sample))

    def test_html_sample_truncated_in_utf8_character_is_still_html(self) -> None:
        prefix = b"<html><body>login "
        for character in ("é", "中", "😀"):
            encoded = character.encode("utf-8")
            for tail_size in range(1, len(encoded)):
                with self.subTest(character=character, tail_size=tail_size):
                    sample = prefix + b" " * (8192 - len(prefix) - tail_size) + encoded[:tail_size]
                    self.assertEqual(8192, len(sample))
                    self.assertTrue(_looks_like_html(sample))


if __name__ == "__main__":
    unittest.main()
