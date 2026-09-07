from __future__ import annotations

import unittest

from zentao_skill.text_contract import compose_bug_steps, decode_json_text, normalize_multiline_text


class TextContractTests(unittest.TestCase):
    def test_composer_joins_known_sections_with_real_lf(self) -> None:
        rendered = compose_bug_steps([
            ("复现步骤", "1. 打开页面\r\n2. 输入 URL=http://localhost:8080?a=1&b=2"),
            ("实际结果", "页面显示错误"),
            ("期望结果", "页面正常显示"),
        ])
        self.assertEqual(
            "复现步骤:\n1. 打开页面\n2. 输入 URL=http://localhost:8080?a=1&b=2\n\n"
            "实际结果:\n页面显示错误\n\n期望结果:\n页面正常显示",
            rendered,
        )

    def test_json_decode_is_one_boundary_and_literal_backslash_n_is_preserved(self) -> None:
        self.assertEqual("第一行\n第二行", decode_json_text('"第一行\\n第二行"'))
        self.assertEqual(r"用户输入字面量 \n", decode_json_text('"用户输入字面量 \\\\n"'))
        self.assertEqual("第一行\n第二行", normalize_multiline_text("第一行\r\n第二行"))


if __name__ == "__main__":
    unittest.main()
