from __future__ import annotations

import unittest

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "zentao" / "scripts"))

from zentao_skill.internal.web_urls import render_bug_web_urls  # noqa: E402


class WebUrlRouteTests(unittest.TestCase):
    def test_fixed_route_supports_single_and_batch_ids_without_network(self) -> None:
        one = render_bug_web_urls("http://localhost", [3641])
        many = render_bug_web_urls("http://localhost", [1, 2, 3, 4, 5])
        self.assertEqual("http://localhost/index.php?m=bug&f=view&bugID=3641", one[0]["url"])
        self.assertEqual(5, len(many))
        self.assertTrue(all(item["source"] == "zentao_standard_route" for item in many))


if __name__ == "__main__":
    unittest.main()
